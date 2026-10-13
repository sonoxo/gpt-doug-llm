#!/usr/bin/env python3
"""Supervise local OSIRIS UI and bounded OSIRIS->PINEAL health synchronization."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import sqlite3
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from bridge import records_from_snapshot, SAFE_ROUTES
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


def pineal_counts() -> dict:
    """Read only aggregate metrics from an existing PINEAL database.

    No SQLite database is created here, and no ontology plaintext leaves it.
    """
    home = Path(os.getenv("PINEAL_HOME", str(Path.home() / ".local/share/gpt-doug-pineal")))
    dbfile = home.expanduser() / "pineal.sqlite3"
    if not dbfile.is_file():
        return {"state": "NOT_INITIALIZED", "feed_health_records": 0, "audit_entries": 0}
    try:
        uri = "file:" + quote(str(dbfile.resolve()), safe="/") + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as db:
            record_count = db.execute(
                "SELECT COUNT(*) FROM memories WHERE namespace = ?",
                ("osiris_feed",)
            ).fetchone()[0]
            audit_count = db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        return {"state": "LOCAL", "feed_health_records": record_count,
                "audit_entries": audit_count,
                "audit_integrity_verified": False}
    except (OSError, sqlite3.Error, ValueError):
        return {"state": "UNAVAILABLE", "feed_health_records": 0, "audit_entries": 0}


def status(port: int) -> dict:
    """Truthful read-only status with stale-feed checks and no raw payloads."""
    snapshot_path = Path(os.getenv("OSIRIS_MIRROR_OUT", str(DEFAULT_SNAPSHOT.parent))) / "snapshot.json"
    output = {
        "dashboard": check_process(port),
        "map_url": f"http://127.0.0.1:{port}/",
        "snapshot_exists": snapshot_path.is_file(),
        "snapshot_generated_at_utc": None,
        "safe_routes": {},
        "pineal": pineal_counts(),
    }
    if not snapshot_path.is_file():
        return output
    try:
        if snapshot_path.stat().st_size > 75_000_000:
            raise ValueError("snapshot exceeds 75 MB")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        # The same strict parser and route allowlist are used by the PINEAL importer.
        records = records_from_snapshot(snapshot, now=time.time(), max_age=600)
        safe_routes = {
            json.loads(record["value"])["route"]: {
                "status": json.loads(record["value"])["status"],
                "last_check_utc": json.loads(record["value"])["last_check_utc"],
                "latency_ms": json.loads(record["value"])["latency_ms"],
                "provenance": "gpt-doug.osiris-safe-mirror.v1",
            }
            for record in records
        }
        generated = snapshot.get("generated_at")
        if isinstance(generated, (int, float)) and not isinstance(generated, bool) and math.isfinite(generated):
            try:
                output["snapshot_generated_at_utc"] = datetime.fromtimestamp(
                    generated, tz=timezone.utc
                ).isoformat()
            except (OSError, OverflowError, ValueError):
                pass
        output["safe_routes"] = safe_routes
        output["snapshot"] = {"safe_routes": safe_routes,
                              "health": {"observed_routes": len(safe_routes),
                                         "fresh_successful_routes": sum(1 for r in safe_routes.values()
                                                                        if r["status"] == "ONLINE"),
                                         "allowed_routes": len(SAFE_ROUTES)}}
    except (OSError, OverflowError, ValueError, TypeError, json.JSONDecodeError) as exc:
        output["snapshot_error"] = "Invalid, untrusted or unavailable public-feed snapshot"
    return output


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


def start(launcher: Path, port: int, interval: int, startup_timeout: int,
          console_port: int = 8766) -> int:
    if not launcher.is_file():
        raise ValueError(f"run.sh not found: {launcher}")
    if console_port == port or not 1024 <= console_port <= 65535:
        raise ValueError("console port must be 1024..65535 and differ from map port")
    if check_process(port)["serving"]:
        print(f"OSIRIS is already running on port {port}; refusing to manage an unrelated process.", file=sys.stderr)
        print("Use 'sh integrations/pineal_osiris/run.sh status' to inspect the local dashboard.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env["OSIRIS_PORT"] = str(port)
    proc = subprocess.Popen(["sh", str(launcher), "run"], env=env, start_new_session=True)
    console = None
    try:
        if not wait_for_http(proc, port, startup_timeout):
            print("OSIRIS did not respond before timeout; check Git, npm and upstream errors above.", file=sys.stderr)
            return 2
        url = f"http://127.0.0.1:{port}/?layers={LAYERS}"
        from console import launch_console
        console = launch_console(console_port, lambda: status(port))
        control_url = f"http://127.0.0.1:{console_port}/"
        print(f"\nOSIRIS VISUAL DASHBOARD: {url}\nPINEAL HEALTH CONSOLE: {control_url}"
              f"\nPINEAL: local-only feed-health sync every {interval}s.", flush=True)
        if platform.system() == "Darwin" and sys.stdout.isatty() and os.getenv("OSIRIS_NO_BROWSER") != "1":
            try:
                subprocess.Popen(["open", control_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        if console is not None:
            console.shutdown()
            console.server_close()
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
    p.add_argument("--startup-timeout", type=int, default=1500)
    p.add_argument("--launcher", type=Path)
    p.add_argument("--console-port", type=int, default=8766)
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
        return start(launcher.resolve(), args.port, args.interval, args.startup_timeout,
                     console_port=args.console_port)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"OSIRIS stack failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
