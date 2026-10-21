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

    rea = sub.add_parser("rea", help="Bounded local REA static analysis (plan-only by default).")
    rea.add_argument("--mode", choices=("javascript", "desktop"), default="javascript")
    rea.add_argument("--target", action="append", required=True, help="Authorized absolute local path; repeatable.")
    rea.add_argument("--output", required=True, help="Existing absolute evidence directory.")
    rea.add_argument("--workers", type=int, default=2)
    rea.add_argument("--timeout", type=int, default=120)
    rea.add_argument("--max-evidence-mib", type=int, default=16)
    rea.add_argument("--execute", action="store_true")
    rea.add_argument("--authorized", action="store_true", help="Declare explicit authority to analyze targets.")

    args = parser.parse_args()
    if args.command == "rea":
        from .rea_swarm import run_cli
        return run_cli(args)
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
