from __future__ import annotations

import argparse
import json

from .capabilities import doctor
from .orchestrator import Hivemind


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-hivemind")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Probe all upstream integrations without changing the system.")

    plan = sub.add_parser("plan", help="Build the deterministic swarm DAG for a job.")
    plan.add_argument("job")
    plan.add_argument("--workers", type=int, default=8)

    status = sub.add_parser("status", help="Show Universal Hive + GPT-Chaos runtime status.")

    summon = sub.add_parser("summon", help="Create a persisted Universal Hive swarm and builder reward event.")
    summon.add_argument("job")
    summon.add_argument("--workers", type=int, default=8)
    summon.add_argument("--builders", default="", help="Comma-separated builder IDs.")
    summon.add_argument("--request-id", default=None, help="Optional idempotency key.")

    run = sub.add_parser("run", help="Run the control plane. Defaults to a non-mutating dry-run.")
    run.add_argument("job")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--execute", action="store_true")

    args = parser.parse_args()

    if args.command == "doctor":
        _print_json([cap.to_dict() for cap in doctor()])
        return 0

    hive = Hivemind(max_workers=getattr(args, "workers", 8))
    if args.command == "status":
        _print_json(hive.hive_status())
        return 0

    if args.command == "summon":
        builders = [x.strip() for x in args.builders.split(",") if x.strip()] or None
        _print_json(hive.summon(args.job, builders=builders, request_id=args.request_id))
        return 0

    if args.command == "plan":
        _print_json(hive.build_plan(args.job).to_dict())
        return 0

    if args.command == "run":
        _print_json(hive.run(args.job, execute=args.execute))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
