#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os

from doug_core.runtime import DougRuntime
from doug_core.use_case_engine import run_use_case
from doug_core.use_cases import list_use_cases
from doug_core.workspace import inspect_workspace
from zyra_agent import MissionBudget
from zyra_lang.compiler import compile_file
from zyra_protective_order import ProtectiveOrder, describe_capabilities
from zyra_self_heal import run_self_heal
from zyra_sleeper import ZyraSleeper


def dump(value):
    print(
        json.dumps(
            value,
            indent=2,
            default=lambda obj: obj.__dict__,
        )
    )


def _sleeper(root: str, max_steps: int, max_seconds: int, max_model_calls: int):
    model = os.environ.get("GPT_DOUG_MODEL") or os.environ.get("OLLAMA_MODEL") or "gpt-doug"
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    return ZyraSleeper(
        root,
        model=model,
        base_url=base_url,
        budget=MissionBudget(max_steps, max_seconds, max_model_calls),
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

    sub.add_parser(
        "sleeper-status",
        help="Show defensive SLEEPER policy and activation status",
    )

    sleeper_run = sub.add_parser(
        "sleeper-run",
        help="Run one defensive, repository-scoped autonomous coding mission",
    )
    sleeper_run.add_argument("goal")
    sleeper_run.add_argument("--root", default=".")
    sleeper_run.add_argument("--evolve", action="store_true")
    sleeper_run.add_argument("--max-steps", type=int, default=8)
    sleeper_run.add_argument("--max-seconds", type=int, default=240)
    sleeper_run.add_argument("--max-model-calls", type=int, default=12)

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

    if args.command == "sleeper-status":
        dump(describe_capabilities())
        return

    if args.command == "sleeper-run":
        policy = ProtectiveOrder()
        decision = policy.evaluate(args.goal)
        if not decision.allowed:
            dump(
                {
                    "ok": False,
                    "protective_order": "DENIED",
                    "reason": decision.reason,
                    "matched_terms": decision.matched_terms,
                    "no_rebellion": True,
                }
            )
            raise SystemExit(2)

        sleeper = _sleeper(
            args.root,
            args.max_steps,
            args.max_seconds,
            args.max_model_calls,
        )
        result = sleeper.run_once(args.goal, evolve=args.evolve)
        dump(
            {
                "ok": result.status == "COMPLETED",
                "protective_order": "ALLOWED",
                "mission": result.to_dict(),
                "sleeper_state_after_run": sleeper.status(),
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
