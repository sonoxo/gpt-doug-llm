"""GPT-Doug BioPineal bounded local swarm.

A software-only model of a persistent memory biochip. No network scanning,
self-propagation, device actuation, or biological hardware integration.
Run: python3 -m research_lab.biochip_swarm --workers 4 --cycles 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

MAX_WORKERS = 8
MAX_CYCLES = 100


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BioChip:
    def __init__(self, path: Path):
        self.path = path
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS memories (digest TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
            self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, stamp TEXT NOT NULL, worker TEXT NOT NULL, event TEXT NOT NULL)")

    def remember(self, payload: dict) -> str:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(text.encode()).hexdigest()
        with self.lock, self.db:
            self.db.execute("INSERT OR IGNORE INTO memories VALUES (?, ?, ?)", (digest, text, now()))
        return digest

    def event(self, worker: str, event: str) -> None:
        with self.lock, self.db:
            self.db.execute("INSERT INTO events (stamp, worker, event) VALUES (?, ?, ?)", (now(), worker, event))

    def report(self) -> dict:
        with self.lock:
            memory_count = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            event_count = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"memory_records": memory_count, "audit_events": event_count, "db": str(self.path)}

    def close(self) -> None:
        self.db.close()


def worker_task(chip: BioChip, worker_id: int, cycle: int, stop: threading.Event) -> None:
    if stop.is_set():
        return
    worker = f"bio-worker-{worker_id:02d}"
    chip.remember({"source": "local-simulation", "worker": worker, "cycle": cycle, "result": "healthy"})
    chip.event(worker, f"heartbeat cycle={cycle}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--db", type=Path, default=Path("biochip-swarm.sqlite3"))
    args = parser.parse_args()
    if not 1 <= args.workers <= MAX_WORKERS:
        parser.error(f"--workers must be 1..{MAX_WORKERS}")
    if not 1 <= args.cycles <= MAX_CYCLES:
        parser.error(f"--cycles must be 1..{MAX_CYCLES}")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    chip = BioChip(args.db)
    stop = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="biochip") as pool:
            for cycle in range(args.cycles):
                jobs = [pool.submit(worker_task, chip, n, cycle, stop) for n in range(args.workers)]
                for job in jobs:
                    job.result()
                chip.event("supervisor", f"cycle={cycle} complete workers={args.workers}")
        print(json.dumps({"status": "completed", "workers": args.workers, "cycles": args.cycles, **chip.report()}, indent=2))
        return 0
    except KeyboardInterrupt:
        stop.set()
        chip.event("supervisor", "stopped by operator")
        print(json.dumps({"status": "stopped", **chip.report()}))
        return 130
    finally:
        chip.close()


if __name__ == "__main__":
    raise SystemExit(main())
