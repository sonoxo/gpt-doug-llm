from __future__ import annotations

import argparse
import json

from .registry import get_member, load_registry, summary, validate_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="north-star", description="THE NORTH STAR FEDERATION registry CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show federation summary")
    sub.add_parser("validate", help="validate the federation registry")
    member = sub.add_parser("member", help="show one federation member")
    member.add_argument("member_id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = load_registry()

    if args.command == "status":
        print(json.dumps(summary(data), indent=2))
        return 0

    if args.command == "validate":
        errors = validate_registry(data)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, indent=2))
            return 1
        print(json.dumps({"valid": True, "member_count": len(data["members"])}, indent=2))
        return 0

    if args.command == "member":
        member = get_member(data, args.member_id)
        if member is None:
            print(json.dumps({"error": "member not found", "member_id": args.member_id}, indent=2))
            return 2
        print(json.dumps(member, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
