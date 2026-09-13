"""JSON input/output interface. No mutation of repositories or live systems."""
import argparse
import json
from pathlib import Path
from . import demo, lineage, reconcile, repair


def main(argv=None):
    parser = argparse.ArgumentParser(prog="doug-max invention-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    for name in ("repair", "reconcile", "lineage"):
        command = sub.add_parser(name)
        command.add_argument("input", type=Path, help="local UTF-8 JSON input; see research_lab/README.md")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo.run()
        else:
            data = json.loads(args.input.read_text(encoding="utf-8"))
            if args.command == "repair":
                result = repair.plan(data["dependencies"], data["changed"], data["tests"], data["revisions"])
            elif args.command == "reconcile":
                result = reconcile.reconcile(data["base"], data["local"], data["remote"])
            else:
                result = lineage.audit(data["claims"], data["documents"])
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        if args.command == "demo":
            return 0 if result["passed"] else 1
        if args.command == "repair":
            return 0 if result["status"] == "PLAN_READY" else 1
        if args.command == "reconcile":
            return 0 if result["apply_allowed"] else 1
        return 1 if result["invalidated"] else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}))
        return 2
