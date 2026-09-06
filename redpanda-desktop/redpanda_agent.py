#!/usr/bin/env python3
"""GPT-REDPANDA DESKTOP/MOBILE: USB-resident local-first assistant + Cyber CPR node.

Design goals:
- Runtime code, state, memory, event stream, and logs can live on a mounted USB drive.
- A small host bootstrap may be installed so macOS can rediscover the USB node.
- Terminal monitoring is metadata-only: exit status + cwd. It does not keylog commands.
- Cyber CPR checks run automatically on failed terminal commands and on a heartbeat.
- Repair execution remains bounded by Cyber CPR's explicit allow-listed config.
- Desktop/mobile portal uses only Python's standard library and an optional local llama.cpp API.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_REPO = os.environ.get("REDPANDA_REPO", "sonoxo/gpt-doug-llm")
DEFAULT_INTERVAL = max(60, int(os.environ.get("REDPANDA_INTERVAL", "180")))
DEFAULT_PORT = int(os.environ.get("REDPANDA_PORT", "8765"))
MODEL_BASE = os.environ.get("GPT_DOUG_API", "http://127.0.0.1:9931/v1").rstrip("/")
MODEL_NAME = os.environ.get("ZYRA_MODEL", "")
NODE_MARKER = ".gpt-redpanda-node"

ROOT = Path(__file__).resolve().parent
USB_ROOT = Path(os.environ.get("REDPANDA_USB_ROOT", ROOT.parent)).resolve()
STATE_ROOT = USB_ROOT / ".redpanda"
LOG_DIR = STATE_ROOT / "logs"
MEMORY_DIR = STATE_ROOT / "memory"
EVENT_DIR = STATE_ROOT / "events"
EVENT_FILE = EVENT_DIR / "terminal-events.tsv"
STATUS_FILE = STATE_ROOT / "status.json"
TOKEN_FILE = STATE_ROOT / "portal-token"
CONFIG_FILE = STATE_ROOT / "cyber-cpr-config.json"
AGENT_LOG = LOG_DIR / "agent.log"

for p in (STATE_ROOT, LOG_DIR, MEMORY_DIR, EVENT_DIR):
    p.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} {message}"
    print(line, flush=True)
    try:
        with AGENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default or {})
    except Exception:
        return default or {}


def ensure_token() -> str:
    try:
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass
    return token


PORTAL_TOKEN = ensure_token()


def run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout)


def cyber_cpr_path() -> str | None:
    candidates = [
        shutil.which("cyber-cpr"),
        str(Path.home() / ".local/bin/cyber-cpr"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def cpr_check(repo: str = DEFAULT_REPO, repair: bool = True, reason: str = "heartbeat") -> dict[str, Any]:
    binary = cyber_cpr_path()
    now = int(time.time())
    if not binary:
        result = {
            "ok": False,
            "exit_code": 127,
            "reason": reason,
            "message": "cyber-cpr is not installed",
            "checked_at": now,
        }
        update_status(cpr=result)
        return result

    cmd = [binary, "check", repo, "--config", str(CONFIG_FILE)]
    if repair:
        cmd.append("--repair")

    try:
        proc = run(cmd, timeout=180)
        output = (proc.stdout or "") + (proc.stderr or "")
        output = output.strip()[-8000:]
        result = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "reason": reason,
            "message": output or "Cyber CPR completed",
            "checked_at": now,
        }
    except Exception as exc:
        result = {
            "ok": False,
            "exit_code": 1,
            "reason": reason,
            "message": f"Cyber CPR error: {exc}",
            "checked_at": now,
        }

    update_status(cpr=result)
    log(f"CPR reason={reason} exit={result['exit_code']}")
    return result


_status_lock = threading.Lock()


def update_status(**parts: Any) -> dict[str, Any]:
    with _status_lock:
        status = read_json(STATUS_FILE, {})
        status.update(parts)
        status["updated_at"] = int(time.time())
        status["usb_root"] = str(USB_ROOT)
        status["repo"] = DEFAULT_REPO
        status["agent_pid"] = os.getpid()
        status["cyber_cpr"] = cyber_cpr_path()
        status["event_file"] = str(EVENT_FILE)
        atomic_json(STATUS_FILE, status)
        return status


def status_snapshot() -> dict[str, Any]:
    status = update_status()
    status["model_api"] = MODEL_BASE
    status["model_online"] = model_online()
    return status


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 20) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise RuntimeError("unexpected JSON payload")
        return data


def model_online() -> bool:
    try:
        request_json(f"{MODEL_BASE}/models", timeout=2)
        return True
    except Exception:
        return False


def local_model_name() -> str:
    if MODEL_NAME:
        return MODEL_NAME
    data = request_json(f"{MODEL_BASE}/models", timeout=5)
    items = data.get("data") or []
    if items and isinstance(items[0], dict):
        return str(items[0].get("id") or "local-model")
    return "local-model"


def local_chat(prompt: str) -> str:
    if not prompt.strip():
        return "Prompt is empty."
    model = local_model_name()
    system = (
        "You are GPT-REDPANDA DESKTOP/MOBILE, a local-first defensive assistant node. "
        "Be concise and explicit about what was actually executed. Never claim background "
        "actions you did not perform. Keep terminal observation metadata-only and use Cyber CPR "
        "for bounded health/recovery checks."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt[:8000]},
        ],
        "stream": False,
        "temperature": 0.25,
        "max_tokens": 512,
    }
    data = request_json(f"{MODEL_BASE}/chat/completions", payload, timeout=180)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(str(data.get("error") or "empty local model response"))
    return str((choices[0].get("message") or {}).get("content") or "").strip()


def parse_event(line: str) -> dict[str, Any] | None:
    # Format: epoch<TAB>exit_status<TAB>cwd
    parts = line.rstrip("\n").split("\t", 2)
    if len(parts) != 3:
        return None
    try:
        return {"ts": int(parts[0]), "status": int(parts[1]), "cwd": parts[2]}
    except ValueError:
        return None


def repo_from_cwd(cwd: str) -> str:
    """Resolve a GitHub owner/repo from the current git remote; fall back safely."""
    path = Path(cwd).expanduser()
    try:
        if not path.exists():
            return DEFAULT_REPO
        proc = run(["git", "-C", str(path), "remote", "get-url", "origin"], timeout=5)
        if proc.returncode != 0:
            return DEFAULT_REPO
        remote = (proc.stdout or "").strip()
        if remote.startswith("git@github.com:"):
            remote = remote.split(":", 1)[1]
        elif "github.com/" in remote:
            remote = remote.split("github.com/", 1)[1]
        else:
            return DEFAULT_REPO
        remote = remote.removesuffix(".git").strip("/")
        pieces = remote.split("/")
        if len(pieces) >= 2 and all(pieces[:2]):
            return f"{pieces[0]}/{pieces[1]}"
    except Exception:
        pass
    return DEFAULT_REPO


class MountGuard(threading.Thread):
    daemon = True

    def __init__(self):
        super().__init__(name="redpanda-mount-guard")
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        marker = USB_ROOT / NODE_MARKER
        while not self.stop_event.wait(5):
            if not marker.exists():
                # Exit so launchd can retry discovery when the USB node is reinserted.
                os._exit(3)


class EventWatcher(threading.Thread):
    daemon = True

    def __init__(self, repo: str):
        super().__init__(name="redpanda-event-watcher")
        self.repo = repo
        self.stop_event = threading.Event()
        self.offset = 0
        self.last_cpr = 0.0

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        log(f"terminal metadata watcher active: {EVENT_FILE}")
        while not self.stop_event.is_set():
            try:
                if EVENT_FILE.exists():
                    size = EVENT_FILE.stat().st_size
                    if size < self.offset:
                        self.offset = 0
                    with EVENT_FILE.open("r", encoding="utf-8", errors="replace") as fh:
                        fh.seek(self.offset)
                        for line in fh:
                            event = parse_event(line)
                            if event:
                                update_status(last_terminal_event=event)
                                if event["status"] != 0:
                                    now = time.time()
                                    if now - self.last_cpr >= 20:
                                        self.last_cpr = now
                                        event_repo = repo_from_cwd(event["cwd"])
                                        cpr_check(event_repo, repair=True, reason=f"terminal-exit-{event['status']}")
                        self.offset = fh.tell()
            except Exception as exc:
                log(f"event watcher error: {exc}")
            self.stop_event.wait(2)


class Heartbeat(threading.Thread):
    daemon = True

    def __init__(self, repo: str, interval: int):
        super().__init__(name="redpanda-heartbeat")
        self.repo = repo
        self.interval = max(60, interval)
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        # Initial check after a short boot delay.
        if not self.stop_event.wait(3):
            cpr_check(self.repo, repair=True, reason="startup")
        while not self.stop_event.wait(self.interval):
            cpr_check(self.repo, repair=True, reason="heartbeat")


HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GPT-REDPANDA</title>
<style>
:root{color-scheme:dark;background:#0a0a0d;color:#f5f5f7;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
body{margin:0;min-height:100vh;background:radial-gradient(circle at 20% 0%,#30144c 0,#0a0a0d 42%);padding:24px}
main{max-width:900px;margin:auto}.hero{display:flex;align-items:center;gap:16px;margin-bottom:18px}.panda{font-size:54px}
h1{margin:0;font-size:clamp(28px,6vw,56px)}.sub{opacity:.72;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#13131a;border:1px solid #2c2c39;border-radius:16px;padding:16px;box-shadow:0 15px 40px #0008}
.label{font-size:12px;opacity:.6}.value{font-size:18px;margin-top:6px;word-break:break-word}.ok{color:#7dff9b}.bad{color:#ff7d8b}
button,input{font:inherit;border-radius:10px;border:1px solid #353545;background:#0d0d12;color:#fff;padding:11px}
button{cursor:pointer;background:#242433}button:hover{background:#303042}
.chat{display:flex;gap:8px;margin-top:12px}.chat input{flex:1}.answer{white-space:pre-wrap;min-height:80px;margin-top:12px}
pre{white-space:pre-wrap;word-break:break-word;max-height:280px;overflow:auto}
</style>
</head>
<body>
<main>
<div class="hero"><div class="panda">🐼</div><div><h1>GPT-REDPANDA</h1><div class="sub">DESKTOP • MOBILE • USB AUTO-AGENT LLM</div></div></div>
<div class="grid">
<div class="card"><div class="label">NODE</div><div id="node" class="value">loading…</div></div>
<div class="card"><div class="label">CYBER CPR</div><div id="cpr" class="value">loading…</div></div>
<div class="card"><div class="label">LOCAL LLM</div><div id="llm" class="value">loading…</div></div>
<div class="card"><div class="label">TERMINAL WATCH</div><div id="term" class="value">loading…</div></div>
</div>
<div class="card" style="margin-top:12px">
<div class="label">CONTROL</div>
<p><button onclick="runCPR()">🚑 Run CPR now</button> <button onclick="refresh()">↻ Refresh</button></p>
<pre id="output">Ready.</pre>
</div>
<div class="card" style="margin-top:12px">
<div class="label">LOCAL ASSISTANT</div>
<div class="chat"><input id="prompt" placeholder="Ask GPT-REDPANDA…"><button onclick="chat()">Send</button></div>
<div id="answer" class="answer">Local llama.cpp model is optional.</div>
</div>
</main>
<script>
const token=new URLSearchParams(location.search).get('token')||'';
const u=p=>p+(p.includes('?')?'&':'?')+'token='+encodeURIComponent(token);
async function refresh(){
 const s=await fetch(u('/api/status')).then(r=>r.json());
 document.getElementById('node').textContent=s.usb_root||'unknown';
 document.getElementById('cpr').textContent=s.cpr?(s.cpr.ok?'✅ HEALTHY':'⚠️ ATTENTION'):(s.cyber_cpr?'READY':'NOT INSTALLED');
 document.getElementById('cpr').className='value '+((s.cpr&&s.cpr.ok)?'ok':'');
 document.getElementById('llm').textContent=s.model_online?'🧠 ONLINE':'○ OFFLINE';
 const e=s.last_terminal_event;
 document.getElementById('term').textContent=e?('exit '+e.status+' • '+e.cwd):'waiting for shell events';
}
async function runCPR(){
 document.getElementById('output').textContent='Running Cyber CPR…';
 const r=await fetch(u('/api/cpr'),{method:'POST'}).then(r=>r.json());
 document.getElementById('output').textContent=r.message||JSON.stringify(r,null,2);refresh();
}
async function chat(){
 const p=document.getElementById('prompt').value;
 document.getElementById('answer').textContent='Thinking locally…';
 const r=await fetch(u('/api/chat'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})}).then(r=>r.json());
 document.getElementById('answer').textContent=r.answer||r.error||'No response';
}
refresh();setInterval(refresh,5000);
</script>
</body></html>"""


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "GPT-REDPANDA/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        log("portal " + (fmt % args))

    def authorized(self) -> bool:
        query = parse_qs(urlparse(self.path).query)
        supplied = (query.get("token") or [""])[0]
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            supplied = auth[7:].strip()
        return secrets.compare_digest(supplied, PORTAL_TOKEN)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if not self.authorized():
            self.send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            self.send_json(status_snapshot())
            return
        if path == "/api/log":
            try:
                lines = AGENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
            except OSError:
                lines = []
            self.send_json({"lines": lines})
            return
        self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not self.authorized():
            self.send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return
        if path == "/api/cpr":
            self.send_json(cpr_check(DEFAULT_REPO, repair=True, reason="portal"))
            return
        if path == "/api/chat":
            length = min(int(self.headers.get("Content-Length", "0") or 0), 32768)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                prompt = str(body.get("prompt") or "")
                answer = local_chat(prompt)
                self.send_json({"answer": answer})
            except urllib.error.URLError as exc:
                self.send_json({"error": f"local model unavailable: {exc}"}, HTTPStatus.SERVICE_UNAVAILABLE)
            except Exception as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)


def lan_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-redpanda", description="USB-resident desktop/mobile assistant + Cyber CPR node")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--lan", action="store_true", help="Bind to LAN for mobile access (token protected)")
    parser.add_argument("--cpr-now", action="store_true", help="Run one CPR pass and exit")
    args = parser.parse_args()

    if not CONFIG_FILE.exists():
        atomic_json(CONFIG_FILE, {"repairs": []})

    if args.cpr_now:
        result = cpr_check(args.repo, repair=True, reason="manual-cli")
        print(result["message"])
        return int(result["exit_code"])

    update_status(state="starting")
    mount_guard = MountGuard()
    watcher = EventWatcher(args.repo)
    heartbeat = Heartbeat(args.repo, args.interval)
    mount_guard.start()
    watcher.start()
    heartbeat.start()

    bind = "0.0.0.0" if args.lan else "127.0.0.1"
    server = ThreadingHTTPServer((bind, args.port), PortalHandler)
    update_status(state="online", bind=bind, port=args.port)

    desktop_url = f"http://127.0.0.1:{args.port}/?token={PORTAL_TOKEN}"
    log("🐼 GPT-REDPANDA ONLINE")
    log(f"desktop portal: {desktop_url}")
    if args.lan:
        log(f"mobile portal: http://{lan_address()}:{args.port}/?token={PORTAL_TOKEN}")
    log("terminal watcher stores exit status + cwd only; command text is not captured")

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        mount_guard.stop()
        watcher.stop()
        heartbeat.stop()
        server.server_close()
        update_status(state="stopped")
        log("GPT-REDPANDA stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
