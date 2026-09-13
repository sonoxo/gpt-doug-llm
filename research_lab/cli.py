"""JSON input/output interface. No mutation of repositories or live systems."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import demo, lineage, reconcile, repair
from .cte import CounterfactualTransactionEngine, ProposedTransition, StateSnapshot


def run_cte(data):
    state_data = data["state"]
    transition_data = data["transition"]

    human_approved = data.get("human_approved", False)
    if not isinstance(human_approved, bool):
        raise TypeError("human_approved must be boolean")

    observed_override = data.get("observed_override")
    if observed_override is not None and not isinstance(observed_override, dict):
        raise TypeError("observed_override must be an object or null")

    state = StateSnapshot(
        version=state_data["version"],
        objects=state_data["objects"],
    )

    transition = ProposedTransition(
        transition_id=transition_data["transition_id"],
        actor=transition_data["actor"],
        changes=transition_data["changes"],
        required_policy=transition_data["required_policy"],
        requires_human_approval=transition_data.get(
            "requires_human_approval",
            True,
        ),
    )

    engine = CounterfactualTransactionEngine()
    return asdict(
        engine.run(
            state,
            transition,
            human_approved=human_approved,
            observed_override=observed_override,
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="doug-max invention-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")

    for name in ("repair", "reconcile", "lineage", "cte"):
        command = sub.add_parser(name)
        command.add_argument(
            "input",
            type=Path,
            help="local UTF-8 JSON input; see research_lab/README.md",
        )

    args = parser.parse_args(argv)

    try:
        if args.command == "demo":
            result = demo.run()
        else:
            data = json.loads(args.input.read_text(encoding="utf-8"))

            if args.command == "repair":
                result = repair.plan(
                    data["dependencies"],
                    data["changed"],
                    data["tests"],
                    data["revisions"],
                )
            elif args.command == "reconcile":
                result = reconcile.reconcile(
                    data["base"],
                    data["local"],
                    data["remote"],
                )
            elif args.command == "lineage":
                result = lineage.audit(
                    data["claims"],
                    data["documents"],
                )
            else:
                result = run_cte(data)

        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))

        if args.command == "demo":
            return 0 if result["passed"] else 1
        if args.command == "repair":
            return 0 if result["status"] == "PLAN_READY" else 1
        if args.command == "reconcile":
            return 0 if result["apply_allowed"] else 1
        if args.command == "lineage":
            return 1 if result["invalidated"] else 0
        if args.command == "cte":
            return 0 if result["status"] == "COMMITTED" else 1

        return 1

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}))
        return 2
