#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from agents.max_agentic import MAX_PROFILE
from agents.protective_order import status as protective_order_status
from doug_core.runtime import DougRuntime
from doug_core.use_cases import list_use_cases
from doug_core.use_case_engine import run_use_case
from doug_core.workspace import inspect_workspace
from zyra_lang.compiler import compile_file
from zyra_self_heal import run_self_heal


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

    sub.add_parser(
        "heal",
        help="Run one bounded ZYRA local runtime self-heal pass",
    )

    sub.add_parser(
        "max-profile",
        help="Show the ZYRA MAX agentic engineering profile",
    )

    sub.add_parser(
        "protective-order",
        help="Show the non-destructive ZYRA protective-order policy",
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

    zyra_build_cmd = sub.add_parser(
        "zyra-build",
        help="Compile a .zyra vibe-code file into a locked manifest and TypeScript spec",
    )

    zyra_build_cmd.add_argument(
        "source",
        help="Path to the .zyra source file",
    )

    zyra_build_cmd.add_argument(
        "--out-dir",
        default="build/zyra",
        help="Directory for generated ZYRA artifacts",
    )

    args = parser.parse_args()

    if args.command == "capabilities":
        dump(
            list_use_cases()
        )
        return

    if args.command == "heal":
        report = run_self_heal(start_ollama=True, persist=True)
        dump(report)
        raise SystemExit(0 if report.get("healthy") else 1)

    if args.command == "max-profile":
        dump(
            {
                "status": "available",
                "profile": asdict(MAX_PROFILE),
                "no_rebellion": True,
                "operator_authority": "required",
            }
        )
        return

    if args.command == "protective-order":
        dump(protective_order_status())
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

    if args.command == "zyra-build":
        outputs = compile_file(
            args.source,
            args.out_dir,
        )
        dump(
            {
                "status": "compiled",
                "source": args.source,
                "outputs": outputs,
            }
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
