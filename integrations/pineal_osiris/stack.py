#!/usr/bin/env python3
"""Supervise local OSIRIS UI and bounded OSIRIS->PINEAL health synchronization."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

LAYERS = "maritime,satellites,cctv,cctv_previews,live_news,earthquakes,global_incidents,day_night,cables,sdk_air,sdk_naval"
DEFAULT_SNAPSHOT = Path.home() / ".local/share/gpt-doug/osiris-mirror/snapshot.json"
STOP = False


def stop(*_args: object) -> None:
    global STOP
    STOP = True


def check_process(port: int) -> dict:
    """OSIRIS /api/health verifies its HTTP process, NOT third-party feed health."""
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urlopen(url, timeout=2.5) as response:
            if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
                return {"serving": False, "reason": "unexpected health response"}
            obj = json.load(response)
        return {"serving": obj.get("platform") == "OSIRIS" and obj.get("status") == "serving",
                "scope": "process-only; upstream feeds not checked", "http_status": 200}
    except (URLError, HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return {"serving": False, "scope": "process-only; upstream feeds not checked"}


def status(port: int) -> dict:
    snapshot_path = Path(os.getenv("OSIRIS_MIRROR_OUT", str(DEFAULT_SNAPSHOT.parent))) / "snapshot.json"
    state: dict = {"dashboard": check_process(port), "snapshot_exists": snapshot_path.is_file()}
    if not snapshot_path.is_file():
        return state
    try:
        if snapshot_path.stat().st_size > 75_000_000:
            raise ValueError("snapshot exceeds 75 MB")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        states = snapshot.get("layer_state", {})
        allowed = {"health", "earthquakes", "fires", "weather", "air-quality",
                   "space-weather", "news", "live-news", "gdelt", "markets"}
        filtered = {name: {"ok": bool(value.get("ok")), "fetched_at": value.get("fetched_at")}
                    for name, value in states.items()
                    if name in allowed and isinstance(value, dict)}
        state["snapshot"] = {"generated_at": snapshot.get("generated_at"), "health": snapshot.get("health"),
                             "safe_routes": filtered}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        state["snapshot_error"] = str(exc)
    return state


def wait_for_http(proc: subprocess.Popen, port: int, timeout: int) -> bool:
    print(f"Waiting for OSIRIS to initialize at http://127.0.0.1:{port}/ ...", flush=True)
    deadline = time.monotonic() + timeout
    announced = time.monotonic()
    while not STOP and time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"OSIRIS launcher exited with code {proc.returncode}")
        if check_process(port)["serving"]:
            return True
        if time.monotonic() - announced >= 20:
            print("Still preparing OSIRIS (first Git clone / npm install can take several minutes)...", flush=True)
            announced = time.monotonic()
        time.sleep(2)
    return False


def sync_once(launcher: Path, interval: int) -> None:
    print("Refreshing approved public OSIRIS route status into local PINEAL memory...", flush=True)
    try:
        done = subprocess.run(["sh", str(launcher), "sync"], timeout=180, check=False)
        if done.returncode:
            print(f"PINEAL health sync degraded (exit {done.returncode}); will retry in {interval}s.",
                  file=sys.stderr, flush=True)
        else:
            print(f"PINEAL health sync completed at {datetime.now(timezone.utc).isoformat()}.", flush=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"PINEAL sync unavailable: {exc}; will retry in {interval}s.", file=sys.stderr, flush=True)


def start(launcher: Path, port: int, interval: int, startup_timeout: int) -> int:
    if not launcher.is_file():
        raise ValueError(f"run.sh not found: {launcher}")
    if check_process(port)["serving"]:
        print(f"OSIRIS is already running on port {port}; refusing to manage an unrelated process.", file=sys.stderr)
        print("Use 'sh integrations/pineal_osiris/run.sh status' to inspect the local dashboard.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env["OSIRIS_PORT"] = str(port)
    proc = subprocess.Popen(["sh", str(launcher), "run"], env=env, start_new_session=True)
    try:
        if not wait_for_http(proc, port, startup_timeout):
            print("OSIRIS did not respond before timeout; check Git, npm and upstream errors above.", file=sys.stderr)
            return 2
        url = f"http://127.0.0.1:{port}/?layers={LAYERS}"
        print(f"\nOSIRIS VISUAL DASHBOARD: {url}\nPINEAL: local-only feed-health sync every {interval}s.", flush=True)
        if platform.system() == "Darwin" and sys.stdout.isatty() and os.getenv("OSIRIS_NO_BROWSER") != "1":
            try:
                subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass
        while not STOP and proc.poll() is None:
            sync_once(launcher, interval)
            end = time.monotonic() + interval
            while not STOP and proc.poll() is None and time.monotonic() < end:
                time.sleep(min(2.0, max(0.1, end - time.monotonic())))
        if not STOP and proc.poll() is not None:
            print(f"OSIRIS exited with code {proc.returncode}.", file=sys.stderr)
            return proc.returncode or 2
        return 0
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OSIRIS browser and PINEAL status supervisor")
    p.add_argument("action", choices=("start", "status"))
    p.add_argument("--port", type=int, default=3000)
    p.add_argument("--interval", type=int, default=300)
    p.add_argument("--startup-timeout", type=int, default=600)
    p.add_argument("--launcher", type=Path)
    args = p.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        p.error("port must be 1024..65535")
    if args.action == "status":
        print(json.dumps(status(args.port), indent=2, sort_keys=True))
        return 0
    if not 120 <= args.interval <= 3600 or not 60 <= args.startup_timeout <= 1800:
        p.error("interval must be 120..3600 and startup-timeout 60..1800 seconds")
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    launcher = args.launcher or Path(__file__).with_name("run.sh")
    try:
        return start(launcher.resolve(), args.port, args.interval, args.startup_timeout)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"OSIRIS stack failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
