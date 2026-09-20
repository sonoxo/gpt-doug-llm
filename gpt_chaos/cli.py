from __future__ import annotations

import argparse
import json

from .runtime import GPTChaos


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-chaos")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show GPT-Chaos + Universal Hive status.")

    summon = sub.add_parser("summon", help="Create a new Universal Hive swarm.")
    summon.add_argument("job")
    summon.add_argument(
        "--builders",
        default="",
        help="Comma-separated builder IDs. Defaults to GPT_DOUG_BUILDERS or operator.",
    )
    summon.add_argument(
        "--request-id",
        default=None,
        help="Optional idempotency key. Reusing it returns the original swarm without a duplicate reward event.",
    )

    args = parser.parse_args()
    chaos = GPTChaos()

    if args.command == "status":
        _print(chaos.status())
        return 0

    if args.command == "summon":
        builders = [x.strip() for x in args.builders.split(",") if x.strip()] or None
        _print(chaos.summon(args.job, builders=builders, request_id=args.request_id))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
