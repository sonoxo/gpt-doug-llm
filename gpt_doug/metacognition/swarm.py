"""Bounded, model-agnostic metacognition primitives for GPT-DOUG.

This module does not create model instances or call external services. It structures
planning, critique, verification, and stopping decisions around supplied artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Candidate:
    text: str
    evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class Review:
    evidence_score: float
    assumption_penalty: float
    risk_penalty: float
    testability_score: float
    confidence: float
    blockers: tuple[str, ...]
    next_action: str

    def to_dict(self) -> dict:
        return asdict(self)


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def review_candidate(candidate: Candidate) -> Review:
    """Score reviewability, not truth; a high score never substitutes for evidence."""
    evidence = _bounded(len(candidate.evidence) / 3)
    assumptions = _bounded(len(candidate.assumptions) / 4)
    risks = _bounded(len(candidate.risks) / 4)
    tests = _bounded(len(candidate.tests) / 3)
    confidence = _bounded(0.35 * evidence + 0.25 * (1 - assumptions)
                          + 0.15 * (1 - risks) + 0.25 * tests)

    blockers = []
    if not candidate.text.strip():
        blockers.append("candidate_text_missing")
    if not candidate.evidence:
        blockers.append("evidence_missing")
    if candidate.assumptions:
        blockers.append("assumptions_require_validation")
    if candidate.risks:
        blockers.append("risks_require_mitigation")
    if not candidate.tests:
        blockers.append("verification_plan_missing")

    if not candidate.text.strip() or not candidate.evidence:
        next_action = "gather_evidence"
    elif candidate.risks or candidate.assumptions:
        next_action = "resolve_assumptions_and_risks"
    elif not candidate.tests:
        next_action = "define_verification"
    else:
        next_action = "human_review_or_policy_gated_execution"

    return Review(evidence, assumptions, risks, tests, confidence,
                  tuple(blockers), next_action)


def run_review_rounds(candidate: Candidate, max_rounds: int = 2) -> list[dict]:
    """Return a finite review trace; no autonomous self-modification or execution."""
    if not isinstance(max_rounds, int) or not 1 <= max_rounds <= 5:
        raise ValueError("max_rounds must be an integer from 1 to 5")
    trace = []
    for round_number in range(1, max_rounds + 1):
        review = review_candidate(candidate)
        trace.append({"round": round_number, "review": review.to_dict()})
        # The supplied candidate is immutable. Stop when no known blockers remain.
        if not review.blockers:
            break
    return trace


def merge_review_signals(reviews: Sequence[Review]) -> dict:
    """Aggregate independent review signals conservatively."""
    if not reviews:
        raise ValueError("at least one review is required")
    blockers = sorted({item for review in reviews for item in review.blockers})
    return {
        "review_count": len(reviews),
        "mean_confidence": round(sum(r.confidence for r in reviews) / len(reviews), 4),
        "blockers": blockers,
        "decision": "hold" if blockers else "eligible_for_gated_review",
        "note": "Scores measure review completeness, not factual correctness.",
    }
