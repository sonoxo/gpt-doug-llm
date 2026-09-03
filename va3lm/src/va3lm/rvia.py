from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from va3lm.mission_ledger import MissionLedger
from va3lm.ontology import CONTROL_PLANE, KERNEL_VERSION
from va3lm.planner import build_plan

MISSION_PROTOCOL = "black-house-mission-v1"
ALLOWED_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "RESTRICTED"}
ALLOWED_APPROVAL_STATES = {"PENDING", "APPROVED", "DENIED"}

CORE_TARGETS: dict[str, dict[str, Any]] = {
    "GPT_DOUG_MAX": {
        "mode": "local-planner",
        "capabilities": {"reasoning", "planning", "evidence"},
    },
    "VIRGINIA": {
        "mode": "local-runtime",
        "capabilities": {"reasoning", "planning", "coding", "evidence"},
    },
    "WAKEUP3LM": {
        "mode": "local-ontology-runtime",
        "capabilities": {"reasoning", "coding", "ontology", "evidence"},
    },
    "ZYRA": {
        "mode": "contract-adapter",
        "capabilities": {"policy", "approval", "security", "audit", "execution"},
    },
    "XUNIA": {
        "mode": "contract-adapter",
        "capabilities": {"apps", "agents", "orchestration", "execution"},
    },
    "NXYZ": {
        "mode": "contract-adapter",
        "capabilities": {"intelligence", "evidence", "integrations"},
    },
    "ZYRA_CLOUD": {
        "mode": "contract-adapter",
        "capabilities": {"compute", "ci", "registry", "artifacts", "deployment"},
    },
    "AIP_REGISTRY": {
        "mode": "contract-adapter",
        "capabilities": {"quality-gate", "tests", "typecheck", "build"},
    },
    "PALANTIR": {
        "mode": "authorized-external-adapter",
        "capabilities": {"ontology", "aip", "foundry", "gotham", "apollo"},
    },
}


class MissionEnvelope(BaseModel):
    missionId: str = Field(default_factory=lambda: str(uuid4()))
    requestedBy: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    target: str = Field(min_length=1)
    classification: str = "INTERNAL"
    requiredCapabilities: list[str] = Field(default_factory=list)
    allowedTools: list[str] = Field(default_factory=list)
    approvalState: str = "PENDING"
    mutation: bool = False
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


Handler = Callable[[MissionEnvelope], dict[str, Any]]


class RVIARouter:
    """Fail-closed Black House mission bus with auditable adapter dispatch."""

    def __init__(self, ledger: MissionLedger | None = None) -> None:
        self.ledger = ledger or MissionLedger()
        self.handlers: dict[str, Handler] = {}
        self.register_handler("GPT_DOUG_MAX", self._planner_handler)
        self.register_handler("VIRGINIA", self._planner_handler)
        self.register_handler("WAKEUP3LM", self._planner_handler)
        for target in ("ZYRA", "XUNIA", "NXYZ", "ZYRA_CLOUD", "AIP_REGISTRY"):
            self.register_handler(target, self._contract_handler)
        self.register_handler("PALANTIR", self._palantir_handler)

    def register_handler(self, target: str, handler: Handler) -> None:
        if target not in CORE_TARGETS:
            raise KeyError(f"Target is not registered in the Black House kernel: {target}")
        self.handlers[target] = handler

    @staticmethod
    def manifest() -> dict[str, Any]:
        return {
            "protocol": MISSION_PROTOCOL,
            "controlPlane": CONTROL_PLANE,
            "kernelVersion": KERNEL_VERSION,
            "failClosed": True,
            "stages": [
                "RVIA",
                "IDENTITY",
                "SHADOW_GLASS",
                "ONTOLOGY_CONTEXT",
                "PLANNER",
                "ZYRA_AUTHORIZATION",
                "DISPATCH",
                "GLASS_ONION",
                "EVIDENCE",
                "AUDIT",
            ],
            "targets": {
                name: {
                    "mode": config["mode"],
                    "capabilities": sorted(config["capabilities"]),
                }
                for name, config in CORE_TARGETS.items()
            },
        }

    def route(self, mission: MissionEnvelope) -> dict[str, Any]:
        envelope = mission.model_dump()
        self.ledger.create(envelope)
        self._audit(mission, "RVIA_RECEIVED", "RVIA", {"protocol": MISSION_PROTOCOL})

        rejection = self._validate(mission)
        if rejection is not None:
            return self._finish(mission, "REJECTED", rejection)

        self._audit(
            mission,
            "SHADOW_GLASS_POLICY",
            "SHADOW_GLASS",
            {"classification": mission.classification, "decision": "ALLOW"},
        )
        self._audit(
            mission,
            "ONTOLOGY_CONTEXT",
            "THE_BLACK_HOUSE",
            {"kernelVersion": KERNEL_VERSION, "target": mission.target},
        )

        if mission.mutation and mission.approvalState != "APPROVED":
            return self._finish(
                mission,
                "APPROVAL_REQUIRED",
                {
                    "accepted": False,
                    "reason": "Mutation missions require explicit ZYRA approval.",
                    "approvalState": mission.approvalState,
                },
            )

        if mission.approvalState == "DENIED":
            return self._finish(
                mission,
                "DENIED",
                {"accepted": False, "reason": "Mission approval state is DENIED."},
            )

        self._audit(
            mission,
            "ZYRA_AUTHORIZATION",
            "ZYRA",
            {
                "mutation": mission.mutation,
                "approvalState": mission.approvalState,
                "decision": "ALLOW",
            },
        )

        handler = self.handlers.get(mission.target)
        if handler is None:
            return self._finish(
                mission,
                "ADAPTER_UNAVAILABLE",
                {"accepted": False, "reason": "No registered runtime adapter."},
            )

        result = handler(mission)
        status = "COMPLETED" if result.get("accepted") else "HOLD"
        return self._finish(mission, status, result)

    def _validate(self, mission: MissionEnvelope) -> dict[str, Any] | None:
        if mission.classification not in ALLOWED_CLASSIFICATIONS:
            return {
                "accepted": False,
                "reason": f"Unknown classification: {mission.classification}",
            }
        if mission.approvalState not in ALLOWED_APPROVAL_STATES:
            return {
                "accepted": False,
                "reason": f"Unknown approval state: {mission.approvalState}",
            }
        if mission.target not in CORE_TARGETS:
            return {"accepted": False, "reason": f"Unknown target: {mission.target}"}
        target_capabilities = CORE_TARGETS[mission.target]["capabilities"]
        missing = sorted(set(mission.requiredCapabilities) - target_capabilities)
        if missing:
            return {
                "accepted": False,
                "reason": "Target does not satisfy required capabilities.",
                "missingCapabilities": missing,
            }
        return None

    def _planner_handler(self, mission: MissionEnvelope) -> dict[str, Any]:
        plan = build_plan(mission.intent)
        return {
            "accepted": True,
            "target": mission.target,
            "adapterMode": CORE_TARGETS[mission.target]["mode"],
            "executionState": "LOCAL_PLAN_COMPLETE",
            "plan": plan,
        }

    @staticmethod
    def _contract_handler(mission: MissionEnvelope) -> dict[str, Any]:
        return {
            "accepted": True,
            "target": mission.target,
            "adapterMode": CORE_TARGETS[mission.target]["mode"],
            "executionState": "MISSION_CONTRACT_ACCEPTED",
            "protocol": MISSION_PROTOCOL,
            "note": (
                "The mission crossed the RVIA bus and reached the registered contract adapter. "
                "External side effects remain governed by that service's authorization boundary."
            ),
        }

    @staticmethod
    def _palantir_handler(mission: MissionEnvelope) -> dict[str, Any]:
        live_verified = bool(mission.metadata.get("palantirLiveVerified"))
        requires_live = bool(mission.metadata.get("requiresLive", True))
        if requires_live and not live_verified:
            return {
                "accepted": False,
                "target": "PALANTIR",
                "adapterMode": "authorized-external-adapter",
                "executionState": "LIVE_TENANT_UNVERIFIED",
                "reason": "Authorized Palantir tenant verification is required before live dispatch.",
            }
        return {
            "accepted": True,
            "target": "PALANTIR",
            "adapterMode": "authorized-external-adapter",
            "executionState": "AUTHORIZED_ADAPTER_ROUTE_READY",
        }

    def _audit(
        self,
        mission: MissionEnvelope,
        event_type: str,
        actor: str,
        details: dict[str, Any],
    ) -> None:
        event = {"eventType": event_type, "actor": actor, "details": details}
        mission.audit.append(event)
        self.ledger.append_event(mission.missionId, event_type, actor, details)

    def _finish(
        self,
        mission: MissionEnvelope,
        status: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        mission.result = result
        evidence = {
            "type": "RouteEvidence",
            "missionId": mission.missionId,
            "target": mission.target,
            "status": status,
            "controlPlane": CONTROL_PLANE,
            "kernelVersion": KERNEL_VERSION,
        }
        mission.evidence.append(evidence)
        self._audit(mission, "GLASS_ONION_EVIDENCE", "GLASS_ONION", evidence)
        envelope = mission.model_dump()
        record = self.ledger.update(
            mission.missionId,
            envelope,
            status=status,
            event_type="MISSION_FINALIZED",
            actor="RVIA",
            details={"status": status},
        )
        return {
            "protocol": MISSION_PROTOCOL,
            "status": status,
            "mission": envelope,
            "record": record,
        }
