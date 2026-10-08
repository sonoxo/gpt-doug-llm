"""Command-line interface for the hardened GPT-ZYRA-Shaggoth bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .bridge import ZyraShaggothBridge


def _dump(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-zyra-shaggoth")
    parser.add_argument(
        "--state-dir",
        default=str(Path.home() / ".gpt-doug" / "zyra-shaggoth"),
        help="Local private state directory.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show the hardened GPT-DOUG binding.")
    sub.add_parser("verify", help="Verify local security invariants.")

    plan = sub.add_parser("plan", help="Produce a read-only GPT-DOUG mission plan.")
    plan.add_argument("goal")

    console = sub.add_parser("console", help="Run the ZYRA Mission Control UI on loopback only.")
    console.add_argument("--port", type=int, default=8790)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bridge = ZyraShaggothBridge(args.state_dir)

    if args.command == "status":
        _dump(bridge.status())
        return 0
    if args.command == "verify":
        result = bridge.verify()
        _dump(result)
        return 0 if result["ok"] else 1
    if args.command == "plan":
        _dump(bridge.plan(args.goal))
        return 0
    if args.command == "console":
        bridge.serve_console(port=args.port)
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
