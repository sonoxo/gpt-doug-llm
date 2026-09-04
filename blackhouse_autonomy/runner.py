#!/usr/bin/env python3
"""Guarded local execution bridge for the Black House.

The runner polls a Git-tracked control manifest and executes only a small,
explicit allowlist of repository-local actions. It never uses shell=True,
sudo, destructive reset/clean operations, or arbitrary command strings.

This lets GitHub act as a durable command bus while the Mac remains the
execution boundary. Secrets stay local in ~/.config/blackhouse/secrets.env.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("BLACKHOUSE_REPO", "~/gpt-doug-llm")).expanduser().resolve()
CONTROL_REF = os.environ.get(
    "BLACKHOUSE_CONTROL_REF",
    "origin/feature/worldmonitor-convergence-adapter-20260904",
)
CONTROL_PATH = os.environ.get("BLACKHOUSE_CONTROL_PATH", "ops/autonomy/control.json")
POLL_SECONDS = max(15, int(os.environ.get("BLACKHOUSE_POLL_SECONDS", "30")))
STATE_DIR = Path(os.environ.get("BLACKHOUSE_STATE_DIR", "~/.blackhouse-autonomy")).expanduser()
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "runner.log"
SECRETS_FILE = Path(
    os.environ.get("BLACKHOUSE_SECRETS_FILE", "~/.config/blackhouse/secrets.env")
).expanduser()
RUNTIME_DIR = REPO / ".blackhouse" / "runtime"

ALLOWED_NPM_SCRIPTS = {"test", "check", "build"}
ALLOWED_PYTHON_SCRIPTS = {
    "the-green-house/bin/worldmonitor-convergence.py",
}

_STOP = False


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(argv: list[str], *, cwd: Path = REPO, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    log("RUN " + " ".join(argv))
    result = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )
    if result.stdout.strip():
        log("STDOUT\n" + result.stdout[-8000:])
    if result.stderr.strip():
        log("STDERR\n" + result.stderr[-8000:])
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(argv)}")
    return result


def load_local_secrets() -> None:
    if not SECRETS_FILE.exists():
        return
    for raw in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def git(*args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], timeout=timeout)


def ensure_repo() -> None:
    if not (REPO / ".git").exists():
        raise RuntimeError(f"repository not found at {REPO}")


def fetch_control() -> dict[str, Any]:
    git("fetch", "--quiet", "origin", timeout=300)
    result = git("show", f"{CONTROL_REF}:{CONTROL_PATH}", timeout=60)
    payload = json.loads(result.stdout)
    if payload.get("schema") != 1:
        raise RuntimeError("unsupported control manifest schema")
    return payload


def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(**updates: Any) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    current = read_state()
    current.update(updates)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def ensure_clean_tree() -> None:
    status = git("status", "--porcelain").stdout.strip()
    if status:
        raise RuntimeError("working tree has local changes; refusing automatic branch switch/pull")


def action_git_sync(action: dict[str, Any]) -> None:
    branch = str(action.get("branch") or "").strip()
    if not branch or branch.startswith("-") or any(ch.isspace() for ch in branch):
        raise RuntimeError("invalid branch")
    ensure_clean_tree()
    git("fetch", "origin", branch)
    local = run(["git", "branch", "--list", branch]).stdout.strip()
    if local:
        git("checkout", branch)
    else:
        git("checkout", "-b", branch, f"origin/{branch}")
    git("pull", "--ff-only", "origin", branch)


def safe_repo_path(raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError("path must remain inside repository")
    resolved = (REPO / rel).resolve()
    if REPO not in resolved.parents and resolved != REPO:
        raise RuntimeError("path escaped repository")
    return resolved


def action_pytest(action: dict[str, Any]) -> None:
    target = str(action.get("target", "tests"))
    path = safe_repo_path(target)
    if not path.exists():
        raise RuntimeError(f"pytest target missing: {target}")
    run([sys.executable, "-m", "pytest", target, "-q"], timeout=1800)


def action_npm(action: dict[str, Any]) -> None:
    script = str(action.get("script", ""))
    if script not in ALLOWED_NPM_SCRIPTS:
        raise RuntimeError(f"npm script not allowed: {script}")
    cwd = safe_repo_path(str(action.get("cwd", ".")))
    run(["npm", "run", script], cwd=cwd, timeout=1800)


def action_python(action: dict[str, Any]) -> None:
    script = str(action.get("script", ""))
    if script not in ALLOWED_PYTHON_SCRIPTS:
        raise RuntimeError(f"python script not allowed: {script}")
    safe_repo_path(script)
    args = action.get("args", [])
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise RuntimeError("python args must be a string list")
    run([sys.executable, script, *args], timeout=1800)


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def action_start_worldmonitor(action: dict[str, Any]) -> None:
    if not os.environ.get("WORLDMONITOR_API_KEY") and not os.environ.get("WM_API_KEY"):
        raise RuntimeError(
            f"WorldMonitor key missing; store it locally in {SECRETS_FILE} as WORLDMONITOR_API_KEY=..."
        )
    host = str(action.get("host", "127.0.0.1"))
    port = int(action.get("port", 8787))
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("WorldMonitor adapter is restricted to loopback")
    if not 1024 <= port <= 65535:
        raise RuntimeError("invalid port")

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    pid_file = RUNTIME_DIR / "worldmonitor.pid"
    out_file = RUNTIME_DIR / "worldmonitor.log"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if process_alive(pid):
                log(f"WorldMonitor already running as PID {pid}")
                return
        except ValueError:
            pass

    log_handle = out_file.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "the-green-house/bin/worldmonitor-convergence.py",
            "--serve",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=os.environ.copy(),
        text=True,
    )
    pid_file.write_text(str(proc.pid) + "\n", encoding="utf-8")
    log(f"WorldMonitor started on http://{host}:{port} as PID {proc.pid}")


def action_healthcheck_worldmonitor(action: dict[str, Any]) -> None:
    region = str(action.get("region", "MENA"))
    window = str(action.get("time_window", "6h"))
    port = int(action.get("port", 8787))
    url = f"http://127.0.0.1:{port}/v1/intelligence/convergence?region={region}&time_window={window}"
    run(["curl", "--fail", "--silent", "--show-error", "--max-time", "30", url], timeout=60)


ACTIONS = {
    "git_sync": action_git_sync,
    "pytest": action_pytest,
    "npm": action_npm,
    "python": action_python,
    "start_worldmonitor": action_start_worldmonitor,
    "healthcheck_worldmonitor": action_healthcheck_worldmonitor,
}


def execute_manifest(manifest: dict[str, Any]) -> None:
    if not manifest.get("enabled", False):
        return
    task_id = str(manifest.get("task_id", "")).strip()
    if not task_id:
        raise RuntimeError("manifest missing task_id")
    state = read_state()
    if state.get("last_completed_task_id") == task_id:
        return

    actions = manifest.get("actions")
    if not isinstance(actions, list) or len(actions) > 20:
        raise RuntimeError("actions must be a list of at most 20 items")

    write_state(active_task_id=task_id, last_error=None)
    log(f"TASK {task_id} START")
    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise RuntimeError("action must be an object")
        kind = str(action.get("type", ""))
        handler = ACTIONS.get(kind)
        if handler is None:
            raise RuntimeError(f"action type not allowed: {kind}")
        log(f"TASK {task_id} ACTION {index}/{len(actions)} {kind}")
        handler(action)
    write_state(
        active_task_id=None,
        last_completed_task_id=task_id,
        last_completed_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        last_error=None,
    )
    log(f"TASK {task_id} COMPLETE")


def stop_handler(_signum: int, _frame: Any) -> None:
    global _STOP
    _STOP = True


def main() -> int:
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    load_local_secrets()
    ensure_repo()
    log(f"Black House autonomy runner online repo={REPO} control={CONTROL_REF}:{CONTROL_PATH}")
    while not _STOP:
        try:
            manifest = fetch_control()
            execute_manifest(manifest)
        except Exception as exc:  # keep daemon alive, record exact failure
            log(f"ERROR {type(exc).__name__}: {exc}")
            write_state(last_error=f"{type(exc).__name__}: {exc}")
        for _ in range(POLL_SECONDS):
            if _STOP:
                break
            time.sleep(1)
    log("Black House autonomy runner stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
