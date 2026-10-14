from __future__ import annotations

import argparse
import json

from .barriers import evaluate_barriers
from .engine import MultiDimensionalEngine
from .problems import MILLENNIUM_PROBLEMS, get_problem


def emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def problem_payload(slug: str) -> dict:
    spec = get_problem(slug)
    return {
        "slug": spec.slug,
        "title": spec.title,
        "status": spec.status,
        "statement": spec.statement,
        "decisive_obligation": spec.decisive_obligation,
        "barriers": list(spec.barriers),
        "dimensions": [item.value for item in spec.dimensions],
        "reference_url": spec.reference_url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-mlm")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show the multi-dimensional Millennium engine status.")

    p_problem = sub.add_parser("problem", help="Show one Millennium problem track.")
    p_problem.add_argument("slug", choices=sorted(MILLENNIUM_PROBLEMS))

    p_matrix = sub.add_parser("matrix", help="Generate bounded proof-search work items.")
    p_matrix.add_argument("--problem", choices=sorted(MILLENNIUM_PROBLEMS), default=None)
    p_matrix.add_argument("--replicates", type=int, default=4)
    p_matrix.add_argument("--limit", type=int, default=64)

    p_barrier = sub.add_parser("barriers", help="Check whether known barriers were addressed.")
    p_barrier.add_argument("problem", choices=sorted(MILLENNIUM_PROBLEMS))
    p_barrier.add_argument("--addressed", default="")

    args = parser.parse_args()
    engine = MultiDimensionalEngine()

    if args.command == "status":
        emit(engine.status())
        return 0

    if args.command == "problem":
        emit(problem_payload(args.slug))
        return 0

    if args.command == "matrix":
        items = engine.work_matrix(
            problem=args.problem,
            replicates=args.replicates,
            limit=args.limit,
        )
        emit(
            {
                "count": len(items),
                "items": [
                    {
                        "id": item.id,
                        "problem": item.problem,
                        "dimension": item.dimension,
                        "role": item.role,
                        "replicate": item.replicate,
                    }
                    for item in items
                ],
            }
        )
        return 0

    if args.command == "barriers":
        addressed = [item.strip() for item in args.addressed.split(",") if item.strip()]
        report = evaluate_barriers(args.problem, addressed)
        emit(
            {
                "problem": report.problem,
                "passed": report.passed,
                "required": list(report.required),
                "addressed": list(report.addressed),
                "missing": list(report.missing),
            }
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
