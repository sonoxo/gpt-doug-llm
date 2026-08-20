from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, Sequence

from .models import (
    DecisionCategory,
    DecisionOption,
    DecisionRequest,
    DecisionResult,
    RankedOption,
    RiskLevel,
)


class DecisionRejected(RuntimeError):
    """Raised when a request falls outside the permitted non-lethal scope."""


_PROHIBITED = {
    DecisionCategory.TARGET_SELECTION,
    DecisionCategory.WEAPON_RELEASE,
    DecisionCategory.FIRE_CONTROL,
    DecisionCategory.STRIKE_PLANNING,
    DecisionCategory.LETHAL_ENGAGEMENT,
    DecisionCategory.OFFENSIVE_CYBER,
}


@dataclass(frozen=True)
class _Weights:
    personnel_safety: float = 0.18
    civilian_safety: float = 0.18
    mission_continuity: float = 0.14
    resilience: float = 0.12
    reversibility: float = 0.10
    policy_fit: float = 0.12
    logistics_feasibility: float = 0.07
    cost_efficiency: float = 0.04
    recovery_speed: float = 0.05


class DecisionEngine:
    """Evidence-aware decision support for non-lethal war-room functions.

    The engine ranks operator-provided options. It does not discover targets,
    recommend weapon employment, execute commands, or authorize actions.
    """

    def __init__(self) -> None:
        self._weights = _Weights()

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        self._validate_scope(request)
        self._validate_request(request)

        evidence_by_id = {item.evidence_id: item for item in request.evidence}
        ranked = [self._rank(option, evidence_by_id) for option in request.options]
        ranked.sort(key=lambda item: item.score, reverse=True)

        top = ranked[0] if ranked else None
        risk = self._risk_level(top, request)
        limitations = self._limitations(request, top)

        return DecisionResult(
            request_id=request.request_id,
            status="DECISION_SUPPORT_ONLY",
            category=request.category,
            ranked_options=tuple(ranked),
            recommended_option_id=top.option_id if top else None,
            requires_human_approval=True,
            risk_level=risk,
            limitations=tuple(limitations),
            provenance={
                "engine": "AEGIS bounded decision engine",
                "mission_id": request.mission_id,
                "principal_id": request.principal_id,
                "environment": request.environment,
            },
        )

    def _validate_scope(self, request: DecisionRequest) -> None:
        if request.category in _PROHIBITED:
            raise DecisionRejected(
                f"{request.category.value} is outside AEGIS decision-support scope"
            )

    def _validate_request(self, request: DecisionRequest) -> None:
        if not request.objective.strip():
            raise ValueError("objective is required")
        if not request.options:
            raise ValueError("at least one option is required")
        option_ids = [option.option_id for option in request.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option_id values must be unique")

    def _rank(self, option: DecisionOption, evidence_by_id: Dict[str, object]) -> RankedOption:
        score = (
            option.personnel_safety * self._weights.personnel_safety
            + option.civilian_safety * self._weights.civilian_safety
            + option.mission_continuity * self._weights.mission_continuity
            + option.resilience * self._weights.resilience
            + option.reversibility * self._weights.reversibility
            + option.policy_fit * self._weights.policy_fit
            + option.logistics_feasibility * self._weights.logistics_feasibility
            + option.cost_efficiency * self._weights.cost_efficiency
            + option.recovery_speed * self._weights.recovery_speed
        )

        linked = [evidence_by_id[eid] for eid in option.evidence_ids if eid in evidence_by_id]
        confidence = mean([getattr(item, "confidence") for item in linked]) if linked else 0.0

        # Evidence affects confidence, not the substantive score itself. This avoids
        # silently converting low-quality evidence into a favorable recommendation.
        rationale = [
            f"personnel_safety={option.personnel_safety:.2f}",
            f"civilian_safety={option.civilian_safety:.2f}",
            f"mission_continuity={option.mission_continuity:.2f}",
            f"resilience={option.resilience:.2f}",
            f"reversibility={option.reversibility:.2f}",
            f"policy_fit={option.policy_fit:.2f}",
        ]
        if not linked:
            rationale.append("no linked evidence; confidence forced to 0.00")

        return RankedOption(
            option_id=option.option_id,
            score=round(score, 4),
            confidence=round(confidence, 4),
            rationale=tuple(rationale),
            evidence_ids=tuple(option.evidence_ids),
        )

    def _risk_level(self, top: RankedOption | None, request: DecisionRequest) -> RiskLevel:
        if top is None or top.confidence < 0.25:
            return RiskLevel.UNKNOWN
        if top.confidence < 0.5:
            return RiskLevel.HIGH
        if top.confidence < 0.75:
            return RiskLevel.MODERATE
        return RiskLevel.LOW

    def _limitations(self, request: DecisionRequest, top: RankedOption | None) -> Sequence[str]:
        limitations = [
            "Decision support only; a human authority remains responsible for the decision.",
            "No targeting, fire-control, weapon-release, strike-planning, lethal-engagement, or offensive-cyber support is provided.",
            "Scores reflect the supplied option attributes and do not establish ground truth.",
        ]
        if top is None or top.confidence < 0.5:
            limitations.append("Evidence confidence is insufficient for a high-confidence recommendation.")
        if request.constraints:
            limitations.append("Constraints are recorded for operator review; policy enforcement should occur in Golden Shield/MITO.")
        return limitations
