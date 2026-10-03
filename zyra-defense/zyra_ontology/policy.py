from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .models import (
    EngagementRecommendation,
    HumanAuthorization,
    ProtectedEntity,
    SimulatedTarget,
    Track,
    WeaponSystemModel,
)


class SafetyViolation(RuntimeError):
    pass


BLOCKED_ACTION_TERMS = {
    "arm",
    "fire",
    "launch",
    "release",
    "detonate",
    "weapon_release",
    "real_target",
    "autonomous_engagement",
}


@dataclass(slots=True)
class SafetyDecision:
    allowed: bool
    reasons: List[str]


class SafetyGovernor:
    """Hard boundary between simulation/advisory logic and real-world actuation."""

    def validate_recommendation(
        self,
        recommendation: EngagementRecommendation,
        target: SimulatedTarget,
        track: Track,
        weapon: WeaponSystemModel | None,
        protected_entities: Iterable[ProtectedEntity] = (),
    ) -> SafetyDecision:
        reasons: List[str] = []

        if not recommendation.advisory_only:
            reasons.append("recommendation must remain advisory-only")
        if not target.synthetic or not track.simulated:
            reasons.append("target and track must be synthetic/simulated")
        if weapon is not None:
            if not weapon.simulation_only:
                reasons.append("weapon-system model must be simulation-only")
            if weapon.has_actuation_interface:
                reasons.append("actuation interfaces are prohibited")

        rec_text = f"{recommendation.recommendation} {recommendation.rationale}".lower()
        if any(term in rec_text for term in BLOCKED_ACTION_TERMS):
            reasons.append("recommendation contains blocked real-world actuation language")

        protected_labels = {p.label.lower() for p in protected_entities}
        if target.label.lower() in protected_labels:
            reasons.append("target label matches a protected entity")

        return SafetyDecision(allowed=not reasons, reasons=reasons)

    def require_simulation_authorization(self, authorization: HumanAuthorization) -> None:
        if authorization.decision.value != "approve_simulation":
            raise SafetyViolation("human authorization for simulation was not granted")
