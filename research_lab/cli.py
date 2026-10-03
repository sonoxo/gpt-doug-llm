"""JSON input/output interface. No mutation of repositories or live systems."""

import argparse
import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

from . import demo, lineage, reconcile, repair
from .cte import (
    CounterfactualTransactionEngine,
    ExecutionJournal,
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


def _host_receipt():
    receipt = os.getenv("ZYRA_CTE_RECEIPT", "").strip()

    if not receipt:
        raise ValueError("ZYRA_CTE_RECEIPT is required")

    return receipt


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
    """Legacy synthetic execution after receipt consumption."""

    if "human_approved" in data:
        raise ValueError("human_approved bypass is disabled")

    state, transition = _cte_objects(data)

    authorizer = ReceiptAuthorizer(
        data["approval_database"],
        _host_approvers(),
    )

    try:
        result = authorizer.execute(
            _host_receipt(),
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


def run_cte_execute_durable(data):
    """Receipt-authorized synthetic execution with durable journal."""

    if "human_approved" in data:
        raise ValueError("human_approved bypass is disabled")

    attempt_id = str(data["attempt_id"]).strip()

    if not attempt_id:
        raise ValueError("attempt_id is required")

    state, transition = _cte_objects(data)

    journal = ExecutionJournal(data["journal_database"])
    authorizer = ReceiptAuthorizer(
        data["approval_database"],
        _host_approvers(),
    )

    try:
        result = authorizer.execute_durable(
            journal,
            attempt_id,
            _host_receipt(),
            state,
            transition,
            data["code_versions"],
            data["data_versions"],
            data["policy_versions"],
            data["now"],
            observed_override=data.get("observed_override"),
        )

        attempt = journal.get(attempt_id)
    finally:
        authorizer.close()
        journal.close()

    output = asdict(result)
    output["attempt_id"] = attempt_id
    output["journal_phase"] = (
        attempt.phase if attempt is not None else None
    )

    return output


def run_cte_status(data):
    """Read durable attempt state and event history."""

    attempt_id = str(data["attempt_id"]).strip()

    if not attempt_id:
        raise ValueError("attempt_id is required")

    journal = ExecutionJournal(data["journal_database"])

    try:
        attempt = journal.get(attempt_id)

        if attempt is None:
            return {
                "status": "NOT_FOUND",
                "attempt_id": attempt_id,
                "events": [],
            }

        events = [
            asdict(event)
            for event in journal.events(attempt_id)
        ]
    finally:
        journal.close()

    return {
        "status": "FOUND",
        "attempt": asdict(attempt),
        "events": events,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="doug-max invention-lab"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("demo")

    for name in (
        "repair",
        "reconcile",
        "lineage",
        "cte",
        "cte-execute",
        "cte-execute-durable",
        "cte-status",
    ):
        command = sub.add_parser(name)
        command.add_argument(
            "input",
            type=Path,
            help=(
                "local UTF-8 JSON input; "
                "see research_lab/README.md"
            ),
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

            elif args.command == "cte-execute":
                result = run_cte_execute(data)

            elif args.command == "cte-execute-durable":
                result = run_cte_execute_durable(data)

            else:
                result = run_cte_status(data)

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
            return (
                0
                if result["status"] == "PLAN_READY"
                else 1
            )

        if args.command == "reconcile":
            return 0 if result["apply_allowed"] else 1

        if args.command == "lineage":
            return 1 if result["invalidated"] else 0

        if args.command in {
            "cte",
            "cte-execute",
            "cte-execute-durable",
        }:
            return (
                0
                if result["status"] == "COMMITTED"
                else 1
            )

        if args.command == "cte-status":
            return (
                0
                if result["status"] == "FOUND"
                else 1
            )

        return 1

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        sqlite3.Error,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "message": str(exc),
                }
            )
        )
        return 2
