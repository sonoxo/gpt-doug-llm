"""CLI for GPT-Doug PeaceLab: offline evidence and reviewable pilot protocol.

No network, model calls, or cloud infrastructure. Field approval is never issued.
"""
import argparse
import json
import sys
from pathlib import Path

from .core import assess, demo, facilitator_kit, review_brief, verify
from .pilot import (pilot_assess, pilot_dashboard_html, pilot_demo,
                    pilot_review_markdown, pilot_verify)


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("missing, symlinked or oversized JSON file")
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def initialize(path, value, label):
    # Exclusive creation; do not replace existing project or pilot records.
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    dump({"created": str(path), "type": label, "contains_only_synthetic_plan": True})


def main(argv=None):
    p = argparse.ArgumentParser(prog="gpt-doug-peacelab")
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("demo", "kit", "pilot-demo", "pilot-kit"):
        sub.add_parser(name)
    for name in ("init", "pilot-init"):
        sub.add_parser(name).add_argument("path", type=Path)
    for name in ("assess", "verify", "brief", "pilot-assess", "pilot-verify", "pilot-brief", "pilot-preview"):
        sub.add_parser(name).add_argument("file", type=Path)
    args = p.parse_args(argv)
    try:
        if args.action == "demo":
            dump(assess(demo()))
        elif args.action == "kit":
            print(facilitator_kit())
        elif args.action == "init":
            initialize(args.path, demo(), "peace-evidence")
        elif args.action == "assess":
            dump(assess(read(args.file)))
        elif args.action == "verify":
            valid = verify(read(args.file))
            dump({"local_report_replay_valid": valid, "external_impact_verified": False})
            return 0 if valid else 1
        elif args.action == "brief":
            print(review_brief(read(args.file)))
        elif args.action == "pilot-demo":
            dump(pilot_assess(pilot_demo()))
        elif args.action == "pilot-kit":
            print(pilot_review_markdown(pilot_assess(pilot_demo())))
        elif args.action == "pilot-init":
            initialize(args.path, pilot_demo(), "90-day-peace-pilot")
        elif args.action == "pilot-assess":
            dump(pilot_assess(read(args.file)))
        elif args.action == "pilot-verify":
            valid = pilot_verify(read(args.file))
            dump({"local_pilot_replay_valid": valid, "external_impact_verified": False,
                  "human_field_authorization": "NEVER_GRANTED_BY_SOFTWARE"})
            return 0 if valid else 1
        elif args.action == "pilot-brief":
            print(pilot_review_markdown(read(args.file)))
        elif args.action == "pilot-preview":
            print(pilot_dashboard_html(read(args.file)))
        return 0
    except (OSError, ValueError, TypeError, OverflowError, json.JSONDecodeError) as exc:
        error = {"status": "ERROR", "error_type": type(exc).__name__, "message": str(exc)[:150]}
        print(json.dumps(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
