#!/usr/bin/env python3
"""Compatibility launcher for The Green House WorldMonitor surface."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch The Green House WorldMonitor surface")
    parser.add_argument("--serve", action="store_true", help="Start the local Green House dashboard")
    parser.add_argument("--port", type=int, default=None, help="Override the local dev port")
    args = parser.parse_args()

    if not args.serve:
        parser.print_help()
        return 0

    script_dir = Path(__file__).resolve().parent
    launcher = script_dir / "run-worldmonitor.sh"
    if not launcher.exists():
        raise SystemExit(f"Green House launcher missing: {launcher}")

    env = os.environ.copy()
    if args.port is not None:
        env["DEV_PORT"] = str(args.port)

    return subprocess.call(["bash", str(launcher)], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
