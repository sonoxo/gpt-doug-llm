#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from doug_core.runtime import DougRuntime
from doug_core.use_cases import list_use_cases
from doug_core.use_case_engine import run_use_case
from doug_core.workspace import inspect_workspace


def dump(value):
    print(
        json.dumps(
            value,
            indent=2,
            default=lambda obj: obj.__dict__,
        )
    )


def main():

    parser = argparse.ArgumentParser(
        prog="dougctl",
        description=(
            "GPT Doug local engineering "
            "command center"
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "capabilities"
    )

    inspect_cmd = sub.add_parser(
        "inspect"
    )

    inspect_cmd.add_argument(
        "path",
        nargs="?",
        default=".",
    )

    run_cmd = sub.add_parser(
        "run"
    )

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
            "research",
            "product",
            "agents",
        ],
    )

    run_cmd.add_argument(
        "path",
        nargs="?",
        default=".",
    )

    analyze_cmd = sub.add_parser(
        "analyze"
    )

    analyze_cmd.add_argument(
        "prompt",
    )

    args = parser.parse_args()

    if args.command == "capabilities":
        dump(
            list_use_cases()
        )
        return

    if args.command == "inspect":
        dump(
            inspect_workspace(
                args.path
            ).to_dict()
        )
        return

    if args.command == "run":
        dump(
            run_use_case(
                args.use_case,
                args.path,
            ).to_dict()
        )
        return

    if args.command == "analyze":

        runtime = DougRuntime()

        analysis = runtime.analyze(
            args.prompt
        )

        dump(
            {
                "task": (
                    analysis["task"].__dict__
                ),
                "routing": [
                    item.__dict__
                    for item
                    in analysis["routing"]
                ],
                "plan": (
                    analysis["plan"]
                ),
                "reasoning": (
                    analysis[
                        "reasoning"
                    ].__dict__
                ),
            }
        )


if __name__ == "__main__":
    main()
