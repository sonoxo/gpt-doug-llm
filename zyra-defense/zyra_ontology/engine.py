from __future__ import annotations

from typing import Dict, Iterable, Optional

from .models import (
    AuditEvent,
    AuthorizationRequest,
    EffectSimulation,
    EngagementRecommendation,
    HumanAuthorization,
    HumanAuthority,
    Mission,
    ProtectedEntity,
    SimulatedTarget,
    Track,
    WeaponSystemModel,
)
from .policy import SafetyGovernor, SafetyViolation
from .store import OntologyStore


class ZyraSimulationEngine:
    def __init__(self, store: OntologyStore, governor: Optional[SafetyGovernor] = None) -> None:
        self.store = store
        self.governor = governor or SafetyGovernor()

    def audit(self, actor: str, action: str, object_id: str | None = None, **details: object) -> AuditEvent:
        return self.store.add(
            AuditEvent(actor=actor, action=action, object_id=object_id, details=dict(details))
        )

    def recommend_simulated_action(
        self,
        mission: Mission,
        target: SimulatedTarget,
        track: Track,
        recommendation: str,
        rationale: str,
        confidence: float,
        weapon_model: WeaponSystemModel | None = None,
        protected_entities: Iterable[ProtectedEntity] = (),
    ) -> EngagementRecommendation:
        if not mission.simulation_only:
            raise SafetyViolation("mission must be simulation-only")

        rec = EngagementRecommendation(
            mission_id=mission.id,
            simulated_target_id=target.id,
            weapon_system_model_id=weapon_model.id if weapon_model else None,
            recommendation=recommendation,
            rationale=rationale,
            confidence=max(0.0, min(1.0, confidence)),
            advisory_only=True,
        )

        decision = self.governor.validate_recommendation(
            rec, target, track, weapon_model, protected_entities
        )
        if not decision.allowed:
            self.audit("ZYRA", "recommendation_blocked", target.id, reasons=decision.reasons)
            raise SafetyViolation("; ".join(decision.reasons))

        self.store.add(rec)
        self.audit("ZYRA", "recommendation_created", rec.id, target_id=target.id)
        return rec

    def request_human_authorization(self, rec: EngagementRecommendation) -> AuthorizationRequest:
        req = AuthorizationRequest(recommendation_id=rec.id)
        self.store.add(req)
        self.audit("ZYRA", "authorization_requested", req.id, recommendation_id=rec.id)
        return req

    def simulate_effect(
        self,
        recommendation: EngagementRecommendation,
        authorization: HumanAuthorization,
        authority: HumanAuthority,
    ) -> EffectSimulation:
        if authorization.authority_id != authority.id:
            raise SafetyViolation("authorization authority mismatch")
        self.governor.require_simulation_authorization(authorization)

        # Deliberately synthetic: no targeting geometry, fire-control solution,
        # real-world coordinates, or command/actuation output is produced.
        score = round(max(0.0, min(1.0, recommendation.confidence)) * 100, 1)
        result: Dict[str, object] = {
            "mode": "simulation_only",
            "outcome": "synthetic_effect_computed",
            "confidence_score": score,
            "real_world_actuation": False,
        }
        effect = EffectSimulation(recommendation_id=recommendation.id, result=result)
        self.store.add(effect)
        self.audit(authority.display_name, "simulation_effect_executed", effect.id)
        return effect
