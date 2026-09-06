#!/usr/bin/env python3
"""GPT-REDPANDA-LLM autonomous bounded CPR runtime.

Runs defensive Cyber CPR health checks continuously and may execute only repair
commands already allow-listed in the existing Cyber CPR configuration. It never
generates arbitrary shell commands or mutates remote settings on its own.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_REPO = os.environ.get("REDPANDA_REPO", "sonoxo/gpt-doug-llm")
DEFAULT_INTERVAL = max(60, int(os.environ.get("REDPANDA_AGENTIC_CPR_INTERVAL", "60")))
VERIFY_DELAY = max(5, int(os.environ.get("REDPANDA_AGENTIC_CPR_VERIFY_DELAY", "15")))
MAX_FAILURES = max(1, int(os.environ.get("REDPANDA_AGENTIC_CPR_MAX_FAILURES", "3")))
COOLDOWN = max(60, int(os.environ.get("REDPANDA_AGENTIC_CPR_COOLDOWN", "300")))

ROOT = Path(__file__).resolve().parent
USB_ROOT = Path(os.environ.get("REDPANDA_USB_ROOT", ROOT.parent)).resolve()
STATE_ROOT = USB_ROOT / ".redpanda"
CONFIG_FILE = STATE_ROOT / "cyber-cpr-config.json"
RUNTIME_STATE = STATE_ROOT / "agentic-cpr-runtime.json"
LOG_FILE = STATE_ROOT / "logs" / "agentic-cpr-runtime.log"
STOP = False


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} {message}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def cyber_cpr() -> str | None:
    for candidate in (shutil.which("cyber-cpr"), str(Path.home() / ".local/bin/cyber-cpr")):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def run_check(repo: str, repair: bool) -> dict[str, Any]:
    binary = cyber_cpr()
    now = int(time.time())
    if not binary:
        return {"ok": False, "exit_code": 127, "checked_at": now, "message": "cyber-cpr not installed"}
    cmd = [binary, "check", repo, "--config", str(CONFIG_FILE)]
    if repair:
        cmd.append("--repair")
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=180)
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()[-12000:]
        return {"ok": proc.returncode == 0, "exit_code": proc.returncode, "checked_at": now, "message": output or "Cyber CPR completed"}
    except Exception as exc:
        return {"ok": False, "exit_code": 1, "checked_at": now, "message": f"Cyber CPR runtime error: {exc}"}


def stop_handler(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def sleep_interruptible(seconds: int) -> None:
    deadline = time.time() + seconds
    while not STOP and time.time() < deadline:
        time.sleep(min(1, max(0, deadline - time.time())))


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-redpanda-agentic-cpr")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    if not CONFIG_FILE.exists():
        atomic_json(CONFIG_FILE, {"repairs": []})

    failures = 0
    streak = 0
    cycle = 0
    cooldown_until = 0
    log(f"🤖 GPT-REDPANDA-LLM Agentic CPR ONLINE repo={args.repo} interval={max(60, args.interval)}s")

    while not STOP:
        cycle += 1
        now = int(time.time())
        in_cooldown = now < cooldown_until
        result = run_check(args.repo, repair=not in_cooldown)
        recovered = False

        if result["ok"]:
            recovered = failures > 0
            failures = 0
            streak += 1
            state = "GREEN"
        else:
            failures += 1
            streak = 0
            state = "RED" if failures >= MAX_FAILURES else "AMBER"
            if failures >= MAX_FAILURES:
                cooldown_until = int(time.time()) + COOLDOWN
                log(f"🛑 circuit breaker: {failures} consecutive failed CPR cycles; cooldown={COOLDOWN}s")
            elif not in_cooldown:
                log(f"🔧 CPR cycle failed; verification scheduled in {VERIFY_DELAY}s")
                sleep_interruptible(VERIFY_DELAY)
                if STOP:
                    break
                verify = run_check(args.repo, repair=False)
                result["verification"] = verify
                if verify["ok"]:
                    recovered = True
                    failures = 0
                    streak = 1
                    state = "GREEN"

        payload = {
            "schema": "gpt-redpanda-llm.agentic-cpr.v1",
            "runtime": "GPT-REDPANDA-LLM",
            "core": "GPT-DOUG-LLM",
            "repo": args.repo,
            "cycle": cycle,
            "health": state,
            "streak": streak,
            "consecutive_failures": failures,
            "cooldown_until": cooldown_until,
            "recovered": recovered,
            "bounded_repairs_only": True,
            "result": result,
            "updated_at": int(time.time()),
        }
        atomic_json(RUNTIME_STATE, payload)
        marker = "✅" if state == "GREEN" else ("⚠️" if state == "AMBER" else "❌")
        log(f"{marker} Agentic CPR {state} cycle={cycle} streak={streak} failures={failures}")
        sleep_interruptible(max(60, args.interval))

    log("GPT-REDPANDA-LLM Agentic CPR stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
