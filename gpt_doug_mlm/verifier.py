from __future__ import annotations

from dataclasses import dataclass

from .barriers import BarrierReport, evaluate_barriers
from .models import ProofClaim


@dataclass(frozen=True)
class VerificationReport:
    claim_id: str
    problem: str
    barrier_report: BarrierReport
    contradiction_free: bool
    independent_verifier_count: int
    evidence_kinds: tuple[str, ...]
    ready_for_formalization: bool


def inspect_claim(claim: ProofClaim, addressed_barriers: list[str] | tuple[str, ...] = ()) -> VerificationReport:
    barrier_report = evaluate_barriers(claim.problem, addressed_barriers)
    kinds = tuple(sorted({item.kind for item in claim.evidence}))
    contradiction_free = not claim.contradiction_found
    ready = (
        barrier_report.passed
        and contradiction_free
        and "proof" in kinds
        and ("symbolic" in kinds or "formal" in kinds)
    )
    return VerificationReport(
        claim_id=claim.claim_id,
        problem=claim.problem,
        barrier_report=barrier_report,
        contradiction_free=contradiction_free,
        independent_verifier_count=len(claim.independent_verifiers),
        evidence_kinds=kinds,
        ready_for_formalization=ready,
    )
