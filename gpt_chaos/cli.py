from __future__ import annotations

import argparse
import json

from .runtime import GPTChaos


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-chaos")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show GPT-Chaos + Universal Hive status.")
    sub.add_parser("blended-wing", help="Show the US-20260274413-A1-derived simulation pattern.")
    sub.add_parser("blended-wing-stress", help="Run the bounded blended-wing concept stress-test checklist.")
    sub.add_parser("digital-clone", help="Show the US-20260279583-A1-derived generalized digital-clone learning pattern.")
    sub.add_parser("matrix-status", help="Show UAP-MATRIX shared-space status.")

    matrix_publish = sub.add_parser("matrix-publish", help="Publish as GPT-Chaos to UAP-MATRIX.")
    matrix_publish.add_argument("channel")
    matrix_publish.add_argument("message")
    matrix_publish.add_argument("--evidence", default=None)

    matrix_propose = sub.add_parser("matrix-propose", help="Create a GPT-Chaos peer proposal.")
    matrix_propose.add_argument("statement")
    matrix_propose.add_argument("--evidence", default=None)

    matrix_vote = sub.add_parser("matrix-vote", help="Vote as GPT-Chaos on a matrix decision.")
    matrix_vote.add_argument("decision_id")
    matrix_vote.add_argument("vote", choices=["SUPPORT", "DISSENT", "ABSTAIN"])
    matrix_vote.add_argument("--evidence", default=None)

    summon = sub.add_parser("summon", help="Create a new Universal Hive swarm.")
    summon.add_argument("job")
    summon.add_argument(
        "--builders",
        default="",
        help="Comma-separated builder IDs. Defaults to GPT_DOUG_BUILDERS or operator.",
    )
    summon.add_argument(
        "--request-id",
        default=None,
        help="Optional idempotency key. Reusing it returns the original swarm without a duplicate reward event.",
    )

    args = parser.parse_args()
    chaos = GPTChaos()

    if args.command == "status":
        _print(chaos.status())
        return 0

    if args.command == "blended-wing":
        _print(chaos.aerospace_pattern())
        return 0

    if args.command == "blended-wing-stress":
        _print(chaos.aerospace_stress_test())
        return 0

    if args.command == "digital-clone":
        _print(chaos.digital_clone_pattern())
        return 0

    if args.command == "matrix-status":
        _print(chaos.matrix.status())
        return 0

    if args.command == "matrix-publish":
        _print(chaos.matrix_publish(args.channel, args.message, evidence=args.evidence))
        return 0

    if args.command == "matrix-propose":
        _print(chaos.matrix_propose(args.statement, evidence=args.evidence))
        return 0

    if args.command == "matrix-vote":
        _print(chaos.matrix_vote(args.decision_id, args.vote, evidence=args.evidence))
        return 0

    if args.command == "summon":
        builders = [x.strip() for x in args.builders.split(",") if x.strip()] or None
        _print(chaos.summon(args.job, builders=builders, request_id=args.request_id))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
