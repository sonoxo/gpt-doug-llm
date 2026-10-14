from __future__ import annotations

from dataclasses import dataclass

from .problems import get_problem


@dataclass(frozen=True)
class BarrierReport:
    problem: str
    passed: bool
    required: tuple[str, ...]
    addressed: tuple[str, ...]
    missing: tuple[str, ...]


def evaluate_barriers(problem: str, addressed: list[str] | tuple[str, ...] | set[str]) -> BarrierReport:
    spec = get_problem(problem)
    supplied = set(addressed)
    missing = tuple(item for item in spec.barriers if item not in supplied)
    return BarrierReport(
        problem=problem,
        passed=not missing,
        required=spec.barriers,
        addressed=tuple(sorted(supplied)),
        missing=missing,
    )
