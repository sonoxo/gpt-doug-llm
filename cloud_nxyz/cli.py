from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CloudNXYZEngine


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cloud-nxyz")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show APM law and Cloud-NXYZ capabilities.")

    plan = sub.add_parser("plan", help="Build an APM-validated provider-neutral cloud plan.")
    plan.add_argument("single_command")
    plan.add_argument("--manifest", required=True)

    apply = sub.add_parser("apply", help="Execute a previously generated plan behind the explicit runtime gate.")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--execute", action="store_true")

    sub.add_parser("template", help="Show the learned Cloud-NXYZ APM template.")

    args = parser.parse_args()
    engine = CloudNXYZEngine(args.root)

    if args.command == "status":
        _print(engine.status())
        return 0
    if args.command == "template":
        _print(engine.learned_template())
        return 0
    if args.command == "plan":
        payload = engine.plan(args.single_command, _load(args.manifest))
        path = engine.write_plan(payload)
        payload = dict(payload)
        payload["written_to"] = str(path)
        _print(payload)
        return 0
    if args.command == "apply":
        _print(engine.execute(_load(args.plan), execute=args.execute))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
