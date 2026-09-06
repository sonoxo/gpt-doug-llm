#!/usr/bin/env python3
"""GPT-REDPANDA-LLM supervisor for the GPT-DOUG-LLM ecosystem.

This process is the native local/USB execution plane: it supervises the Red Panda
portal runtime and the bounded autonomous Agentic CPR runtime as one service.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
USB_ROOT = Path(os.environ.get("REDPANDA_USB_ROOT", ROOT.parent)).resolve()
STOP = False
CHILDREN: list[subprocess.Popen[Any]] = []


def handle_stop(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def spawn(args: list[str]) -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env["REDPANDA_USB_ROOT"] = str(USB_ROOT)
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.Popen(args, env=env)
    CHILDREN.append(proc)
    return proc


def stop_children() -> None:
    for proc in CHILDREN:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 5
    while time.time() < deadline and any(p.poll() is None for p in CHILDREN):
        time.sleep(0.1)
    for proc in CHILDREN:
        if proc.poll() is None:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-redpanda-llm", description="GPT-DOUG-LLM local autonomous runtime plane")
    parser.add_argument("--repo", default=os.environ.get("REDPANDA_REPO", "sonoxo/gpt-doug-llm"))
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--port", type=int, default=int(os.environ.get("REDPANDA_PORT", "8765")))
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    python = sys.executable
    portal_cmd = [python, str(ROOT / "redpanda_agent.py"), "--repo", args.repo, "--port", str(args.port)]
    if args.lan:
        portal_cmd.append("--lan")
    cpr_cmd = [python, str(ROOT / "agentic_cpr_runtime.py"), "--repo", args.repo]

    print("🐼 GPT-REDPANDA-LLM merged runtime ONLINE", flush=True)
    print(f"🧠 Core: GPT-DOUG-LLM | repo={args.repo}", flush=True)
    portal = spawn(portal_cmd)
    cpr = spawn(cpr_cmd)

    exit_code = 0
    try:
        while not STOP:
            if portal.poll() is not None:
                print(f"❌ portal runtime exited code={portal.returncode}", flush=True)
                exit_code = int(portal.returncode or 1)
                break
            if cpr.poll() is not None:
                print(f"❌ Agentic CPR runtime exited code={cpr.returncode}", flush=True)
                exit_code = int(cpr.returncode or 1)
                break
            time.sleep(0.5)
    finally:
        stop_children()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
