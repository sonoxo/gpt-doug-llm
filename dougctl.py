#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from doug_core.use_cases import list_use_cases
from doug_core.use_case_engine import run_use_case
from doug_core.workspace import inspect_workspace


def main():
    parser = argparse.ArgumentParser(
        prog="dougctl",
        description="GPT Doug local command center",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("capabilities")

    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("path", nargs="?", default=".")

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument(
        "use_case",
        choices=[
            "build",
            "debug",
            "architect",
            "operator",
            "security",
            "release",
            "docs",
        ],
    )
    run_cmd.add_argument("path", nargs="?", default=".")

    args = parser.parse_args()

    if args.command == "capabilities":
        print(json.dumps(list_use_cases(), indent=2))
        return

    if args.command == "inspect":
        print(
            json.dumps(
                inspect_workspace(args.path).to_dict(),
                indent=2,
            )
        )
        return

    if args.command == "run":
        result = run_use_case(args.use_case, args.path)
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
