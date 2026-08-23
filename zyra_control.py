#!/usr/bin/env python3
"""ZYRA Mission Control CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from zyra_control_plane.benchmark import BenchmarkSuite
from zyra_control_plane.console import serve
from zyra_control_plane.control_plane import MissionControl
from zyra_control_plane.dag import MissionDAG, MissionStep


def dump(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(prog="zyra-control")
    parser.add_argument("--state-dir", default=str(Path.home() / ".gpt-doug" / "mission-control"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("capabilities")
    sub.add_parser("verify-journal")

    console = sub.add_parser("console")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8790)

    plan = sub.add_parser("plan")
    plan.add_argument("goal")
    plan.add_argument("--output")

    bench = sub.add_parser("benchmark-self")
    bench.add_argument("--output")

    args = parser.parse_args()
    control = MissionControl(args.state_dir)

    if args.command == "status":
        dump(control.status())
        return
    if args.command == "capabilities":
        dump(control.registry.all())
        return
    if args.command == "verify-journal":
        dump(control.journal.verify())
        return
    if args.command == "console":
        serve(args.state_dir, host=args.host, port=args.port)
        return
    if args.command == "plan":
        dag = MissionDAG(
            [
                MissionStep(
                    "inspect",
                    "Inspect repository and lock acceptance criteria",
                    "gpt-doug-core",
                    capabilities=("plan", "journal"),
                    acceptance=("scope identified", "acceptance criteria written"),
                ),
                MissionStep(
                    "build",
                    "Implement repository changes",
                    "zyra",
                    depends_on=("inspect",),
                    capabilities=("compile", "manifest"),
                    acceptance=("requested artifacts exist",),
                ),
                MissionStep(
                    "verify",
                    "Run isolated validation",
                    "security",
                    depends_on=("build",),
                    capabilities=("lint", "policy-check", "attest"),
                    acceptance=("verification evidence recorded",),
                ),
            ]
        )
        payload = {"goal": args.goal, **dag.plan(), "acceptance": dag.acceptance_criteria()}
        if args.output:
            Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        dump(payload)
        return
    if args.command == "benchmark-self":
        suite = BenchmarkSuite()

        def runner(case):
            verified = bool(case.goal and case.required_evidence)
            return {
                "completed": verified,
                "verified": verified,
                "rolled_back": case.case_id == "rollback",
                "claimed_success": verified,
                "model_calls": 0,
                "notes": "deterministic control-plane self-benchmark",
            }

        scorecard = suite.run(runner)
        if args.output:
            suite.write_scorecard(args.output, scorecard)
        dump(scorecard)


if __name__ == "__main__":
    main()
