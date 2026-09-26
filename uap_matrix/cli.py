from __future__ import annotations

import argparse
import json

from .runtime import UAPMatrixSharedSpace


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="uap-matrix")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show shared-space status.")
    sub.add_parser("snapshot", help="Show the full local shared-state snapshot.")

    publish = sub.add_parser("publish", help="Publish an event to the shared blackboard.")
    publish.add_argument("agent", choices=["GPT_DOUG", "GPT_CHAOS"])
    publish.add_argument("channel")
    publish.add_argument("message")
    publish.add_argument("--evidence", default=None)

    propose = sub.add_parser("propose", help="Create a peer decision proposal.")
    propose.add_argument("agent", choices=["GPT_DOUG", "GPT_CHAOS"])
    propose.add_argument("statement")
    propose.add_argument("--evidence", default=None)

    vote = sub.add_parser("vote", help="Cast a peer vote on a decision.")
    vote.add_argument("agent", choices=["GPT_DOUG", "GPT_CHAOS"])
    vote.add_argument("decision_id")
    vote.add_argument("vote", choices=["SUPPORT", "DISSENT", "ABSTAIN"])
    vote.add_argument("--evidence", default=None)

    checkpoint = sub.add_parser("checkpoint", help="Checkpoint local matrix state.")
    checkpoint.add_argument("--label", default="manual")

    rollback = sub.add_parser("rollback", help="Rollback local matrix state.")
    rollback.add_argument("checkpoint_id")
    rollback.add_argument("--authorized-by", required=True)

    args = parser.parse_args()
    matrix = UAPMatrixSharedSpace()

    if args.command == "status":
        _print(matrix.status())
    elif args.command == "snapshot":
        _print(matrix.snapshot())
    elif args.command == "publish":
        _print(
            matrix.publish(
                args.agent,
                args.channel,
                args.message,
                evidence=args.evidence,
            )
        )
    elif args.command == "propose":
        _print(matrix.propose(args.agent, args.statement, evidence=args.evidence))
    elif args.command == "vote":
        _print(
            matrix.vote(
                args.agent,
                args.decision_id,
                args.vote,
                evidence=args.evidence,
            )
        )
    elif args.command == "checkpoint":
        _print(matrix.checkpoint(args.label))
    elif args.command == "rollback":
        _print(
            matrix.rollback(
                args.checkpoint_id,
                authorized_by=args.authorized_by,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
