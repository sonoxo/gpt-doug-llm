"""JSON input/output interface. No mutation of repositories or live systems."""
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from . import demo, lineage, reconcile, repair
from .cte import (
    CounterfactualTransactionEngine,
    ProposedTransition,
    ReceiptAuthorizer,
    StateSnapshot,
)


def _cte_objects(data):
    state_data = data["state"]
    transition_data = data["transition"]

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

    return state, transition


def _host_approvers():
    raw = os.getenv("ZYRA_CTE_APPROVERS", "")
    approvers = frozenset(
        value.strip()
        for value in raw.split(",")
        if value.strip()
    )

    if not approvers:
        raise ValueError(
            "ZYRA_CTE_APPROVERS host allowlist is required"
        )

    return approvers


def run_cte(data):
    """Counterfactual proposal/dry-run only. Cannot self-approve."""

    if "human_approved" in data:
        raise ValueError(
            "human_approved bypass is disabled; "
            "authorized execution requires cte-execute"
        )

    state, transition = _cte_objects(data)

    result = CounterfactualTransactionEngine().run(
        state,
        transition,
        human_approved=False,
    )

    return asdict(result)


def run_cte_execute(data):
    """Execute synthetic CTE transaction only after receipt consumption."""

    if "human_approved" in data:
        raise ValueError("human_approved bypass is disabled")

    receipt = os.getenv("ZYRA_CTE_RECEIPT", "").strip()
    if not receipt:
        raise ValueError("ZYRA_CTE_RECEIPT is required")

    state, transition = _cte_objects(data)

    authorizer = ReceiptAuthorizer(
        data["approval_database"],
        _host_approvers(),
    )

    try:
        result = authorizer.execute(
            receipt,
            state,
            transition,
            data["code_versions"],
            data["data_versions"],
            data["policy_versions"],
            data["now"],
            observed_override=data.get("observed_override"),
        )
    finally:
        authorizer.close()

    return asdict(result)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="doug-max invention-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")

    for name in (
        "repair",
        "reconcile",
        "lineage",
        "cte",
        "cte-execute",
    ):
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
            data = json.loads(
                args.input.read_text(encoding="utf-8")
            )

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
            elif args.command == "cte":
                result = run_cte(data)
            else:
                result = run_cte_execute(data)

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )

        if args.command == "demo":
            return 0 if result["passed"] else 1

        if args.command == "repair":
            return 0 if result["status"] == "PLAN_READY" else 1

        if args.command == "reconcile":
            return 0 if result["apply_allowed"] else 1

        if args.command == "lineage":
            return 1 if result["invalidated"] else 0

        if args.command in {"cte", "cte-execute"}:
            return 0 if result["status"] == "COMMITTED" else 1

        return 1

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "message": str(exc),
                }
            )
        )
        return 2
