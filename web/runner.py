"""Runs real project servers (Node/Python) as child processes.

Static projects (just an index.html) are still served directly by the main
server via the /preview/ static route in server.py — this module only
handles projects that need to actually execute: package.json apps, Flask/
plain Python scripts, etc. Each running project gets its own OS-assigned
port; the browser iframe points straight at http://localhost:<port>/.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections import deque

from web import crypto_store


def decrypt_tree(src, dst):
    """Copy a project directory to dst, decrypting any file crypto_store
    encrypted at rest. Files that were never encrypted pass through as-is."""
    os.makedirs(dst, exist_ok=True)
    for root, _dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        out_root = dst if rel_root == "." else os.path.join(dst, rel_root)
        os.makedirs(out_root, exist_ok=True)
        for name in files:
            src_path = os.path.join(root, name)
            with open(src_path, "rb") as f:
                raw = f.read()
            try:
                data = crypto_store.decrypt_bytes(raw)
            except ValueError:
                data = raw  # different key / corrupt — leave as-is, don't crash the run
            with open(os.path.join(out_root, name), "wb") as f:
                f.write(data)


class ProjectProcess:
    def __init__(self, name, cwd, cmd, port, env, run_dir=None):
        self.name = name
        self.cwd = cwd
        self.cmd = cmd
        self.port = port
        self.run_dir = run_dir  # ephemeral decrypted copy actually executed from
        self.logs = deque(maxlen=500)
        self.started_at = time.time()
        self.process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._pump_logs, daemon=True)
        self._reader.start()

    def _pump_logs(self):
        try:
            for line in self.process.stdout:
                self.logs.append(line.rstrip("\n"))
        except Exception:
            pass

    def alive(self):
        return self.process.poll() is None

    def stop(self, timeout=5):
        if not self.alive():
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)


class ProjectRunner:
    """Tracks at most one running child process per project name."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running: dict[str, ProjectProcess] = {}

    def _free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def detect_entry(self, base):
        """Return (cmd_list, kind) for an executable project, or None if
        this looks like a plain static site (server.py falls back to
        serving index.html directly in that case)."""
        pkg_path = os.path.join(base, "package.json")
        if os.path.isfile(pkg_path):
            if not shutil.which("npm"):
                return None
            try:
                with open(pkg_path, "rb") as f:
                    raw = f.read()
                pkg = json.loads(crypto_store.decrypt_bytes(raw))
            except (OSError, ValueError, json.JSONDecodeError):
                pkg = {}
            scripts = pkg.get("scripts", {})
            if "start" in scripts:
                return (["npm", "start"], "node")
            for entry in ("index.js", "server.js", "app.js"):
                if os.path.isfile(os.path.join(base, entry)) and shutil.which("node"):
                    return (["node", entry], "node")
            return None

        python_bin = shutil.which("python3") or shutil.which("python")
        if python_bin:
            for entry in ("app.py", "main.py", "server.py"):
                if os.path.isfile(os.path.join(base, entry)):
                    return ([python_bin, entry], "python")
        return None

    def start(self, name, base):
        with self._lock:
            existing = self._running.get(name)
            if existing and existing.alive():
                return {"ok": True, "already_running": True, "port": existing.port}

            entry = self.detect_entry(base)
            if entry is None:
                return {"ok": False, "error": "no runnable entry point (package.json start script, index.js, app.py, main.py)"}
            cmd, kind = entry

            # Project files are encrypted at rest; decrypt into a private
            # ephemeral copy to actually run from, so the on-disk originals
            # under projects/ stay ciphertext the whole time.
            run_dir = tempfile.mkdtemp(prefix=f"doug-run-{name}-")
            decrypt_tree(base, run_dir)

            port = self._free_port()
            env = {**os.environ, "PORT": str(port), "HOST": "127.0.0.1"}
            try:
                proc = ProjectProcess(name, run_dir, cmd, port, env, run_dir=run_dir)
            except OSError as err:
                shutil.rmtree(run_dir, ignore_errors=True)
                return {"ok": False, "error": f"failed to launch: {err}"}
            self._running[name] = proc
            return {"ok": True, "already_running": False, "port": port, "kind": kind, "cmd": " ".join(cmd)}

    def status(self, name):
        with self._lock:
            proc = self._running.get(name)
            if not proc:
                return {"running": False, "port": None, "logs": []}
            if not proc.alive():
                logs = list(proc.logs)
                del self._running[name]
                self._cleanup(proc)
                return {"running": False, "port": None, "logs": logs, "exited": True}
            return {"running": True, "port": proc.port, "logs": list(proc.logs)}

    def stop(self, name):
        with self._lock:
            proc = self._running.pop(name, None)
        if not proc:
            return {"ok": True, "was_running": False}
        proc.stop()
        self._cleanup(proc)
        return {"ok": True, "was_running": True}

    def list_running(self):
        with self._lock:
            procs = list(self._running.items())
        out = []
        for name, proc in procs:
            out.append({
                "name": name,
                "alive": proc.alive(),
                "port": proc.port,
                "pid": proc.process.pid,
                "started_at": proc.started_at,
                "uptime_s": round(time.time() - proc.started_at, 1),
                "cmd": " ".join(proc.cmd),
            })
        return out

    def stop_all(self):
        with self._lock:
            procs = list(self._running.values())
            self._running.clear()
        for proc in procs:
            proc.stop()
            self._cleanup(proc)

    def _cleanup(self, proc):
        if proc.run_dir:
            shutil.rmtree(proc.run_dir, ignore_errors=True)
