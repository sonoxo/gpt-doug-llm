"""CLI for the GPT-Doug PeaceLab: no network, no cloud resources."""
import argparse
import json
import sys
from pathlib import Path
from .core import assess, demo, facilitator_kit, review_brief, verify


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("missing, symlinked or oversized JSON file")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="gpt-doug-peacelab")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("demo")
    sub.add_parser("kit")
    init = sub.add_parser("init"); init.add_argument("path", type=Path)
    for name in ("assess", "verify", "brief"):
        sub.add_parser(name).add_argument("file", type=Path)
    args = p.parse_args(argv)
    try:
        if args.action == "demo":
            print(json.dumps(assess(demo()), indent=2, sort_keys=True))
        elif args.action == "kit":
            print(facilitator_kit())
        elif args.action == "init":
            with args.path.open("x", encoding="utf-8") as f:
                f.write(json.dumps(demo(), indent=2) + "\n")
            print(json.dumps({"created": str(args.path), "contains_only_synthetic_plan": True}))
        elif args.action == "assess":
            print(json.dumps(assess(read(args.file)), indent=2, sort_keys=True))
        elif args.action == "verify":
            valid = verify(read(args.file))
            print(json.dumps({"local_report_replay_valid": valid, "external_impact_verified": False}))
            return 0 if valid else 1
        elif args.action == "brief":
            print(review_brief(read(args.file)))
        return 0
    except (OSError, ValueError, TypeError, OverflowError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error_type": type(exc).__name__, "message": str(exc)[:150]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
