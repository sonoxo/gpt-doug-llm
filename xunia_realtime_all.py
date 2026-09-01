"""Start the free XUNIA realtime runtime and optional change watcher together."""

from __future__ import annotations

import argparse
import os
import threading

from xunia_realtime_runtime import DEFAULT_DB, DEFAULT_HOST, DEFAULT_PORT, MAX_GLOBAL_WORKERS, serve
from xunia_realtime_watch import run as run_watcher


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the complete free local XUNIA realtime stack")
    parser.add_argument("--host", default=os.getenv("XUNIA_RUNTIME_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("XUNIA_RUNTIME_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--db", default=os.getenv("XUNIA_RUNTIME_DB", DEFAULT_DB))
    parser.add_argument("--workers", type=int, default=int(os.getenv("XUNIA_RUNTIME_WORKERS", str(MAX_GLOBAL_WORKERS))))
    parser.add_argument("--watch-config", default=os.getenv("XUNIA_WATCH_CONFIG"))
    args = parser.parse_args()

    if args.watch_config:
        watcher = threading.Thread(
            target=run_watcher,
            args=(args.watch_config,),
            name="xunia-change-watcher",
            daemon=True,
        )
        watcher.start()
        print(f"XUNIA change watcher loaded from {args.watch_config}")

    serve(args.host, args.port, args.db, args.workers)


if __name__ == "__main__":
    main()
