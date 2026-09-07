"""Palantir-backed backbone for ZYRAPALANTIR.

The backbone binds ZYRAPALANTIR's synthetic digital-twin graph to the existing
FoundryClient without granting ambient authority. Foundry is used as the
semantic/data backbone; state-changing infrastructure behavior remains local
simulation unless a tenant-side *simulation* workflow is deliberately staged
for human review.

No arbitrary Foundry Action execution is exposed from this module.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

from palantir_foundry import FoundryClient
from .core import DigitalTwinAsset, SafetyViolation, ZyraPalantir


SIMULATION_OBJECT_TYPES = {
    "ZyraDivision",
    "ZyraInfrastructureDomain",
    "ZyraDigitalTwinAsset",
    "ZyraDependency",
    "ZyraSyntheticSensor",
    "ZyraSyntheticAlert",
    "ZyraIncident",
    "ZyraSafetyEnvelope",
    "ZyraFailoverResource",
    "ZyraRecoveryStep",
    "ZyraAuditEvent",
}

SAFE_STAGED_ACTIONS = {
    "DECLARE_EXERCISE",
    "ACKNOWLEDGE_INCIDENT",
    "ISOLATE_SIMULATED_NODE",
    "ENTER_SIMULATED_SAFE_STATE",
    "PRESERVE_LIFE_SAFETY_SERVICE",
    "ACTIVATE_SIMULATED_FAILOVER",
    "REROUTE_SIMULATED_EMS",
    "ROLLBACK_SIMULATION_ACTION",
    "RESTORE_SIMULATED_SERVICE",
    "VERIFY_RECOVERY",
    "CLOSE_EXERCISE",
}


@dataclass(frozen=True)
class PalantirBinding:
    ontology: str
    connected: bool
    mode: str
    writes_from_backbone: bool
    tenant_actions: str
    human_review: str
    outbound_actuation: bool


class ZyraPalantirBackbone:
    """Ontology-first adapter between ZYRAPALANTIR and Palantir Foundry.

    Design:
      * Palantir Ontology is the canonical semantic graph when configured.
      * Local ZYRAPALANTIR remains the execution surface for resilience drills.
      * Tenant-side changes are emitted only as *staged action requests* for
        review; this module intentionally never invokes FoundryClient.apply_action.
      * The adapter rejects non-simulation object types and real-world actuator
        metadata.
    """

    MODE = "PALANTIR_BACKBONE_SIMULATION_ONLY"

    def __init__(
        self,
        twin: Optional[ZyraPalantir] = None,
        foundry: Optional[FoundryClient] = None,
        ontology: Optional[str] = None,
    ) -> None:
        self.twin = twin or ZyraPalantir()
        self.foundry = foundry
        self.ontology = (ontology or os.getenv("ZYRAPALANTIR_ONTOLOGY", "")).strip()

    @classmethod
    def from_environment(cls, twin: Optional[ZyraPalantir] = None) -> "ZyraPalantirBackbone":
        return cls(
            twin=twin,
            foundry=FoundryClient.from_environment(),
            ontology=os.getenv("ZYRAPALANTIR_ONTOLOGY", "").strip(),
        )

    def binding(self) -> PalantirBinding:
        return PalantirBinding(
            ontology=self.ontology,
            connected=self.foundry is not None and bool(self.ontology),
            mode=self.MODE,
            writes_from_backbone=False,
            tenant_actions="staged-for-human-review-only",
            human_review="required",
            outbound_actuation=False,
        )

    def status(self) -> dict[str, Any]:
        foundry_status: dict[str, Any]
        if self.foundry is None:
            foundry_status = {"configured": False}
        else:
            foundry_status = self.foundry.status()

        return {
            "division": ZyraPalantir.DIVISION,
            "codename": ZyraPalantir.CODENAME,
            "backbone": asdict(self.binding()),
            "foundry": foundry_status,
            "local_twin": self.twin.status(),
            "safety": {
                "real_infrastructure_write_access": False,
                "real_scada_control": False,
                "real_plc_control": False,
                "real_emergency_service_control": False,
                "real_traffic_control": False,
                "arbitrary_foundry_actions": False,
            },
        }

    def list_remote_object_types(self) -> dict[str, Any]:
        """Read the configured Ontology object-type catalog from Foundry."""
        self._require_foundry()
        return self.foundry.list_object_types(self.ontology)  # type: ignore[union-attr]

    def list_simulation_objects(
        self,
        object_type: str,
        *,
        page_size: int = 100,
        select: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Read only allowlisted ZYRAPALANTIR simulation object types."""
        self._require_foundry()
        self._require_simulation_object_type(object_type)
        return self.foundry.list_objects(  # type: ignore[union-attr]
            self.ontology,
            object_type,
            page_size=page_size,
            select=select,
        )

    def search_simulation_objects(
        self,
        object_type: str,
        search_body: dict[str, Any],
    ) -> dict[str, Any]:
        """Search only allowlisted simulation object types in Foundry."""
        self._require_foundry()
        self._require_simulation_object_type(object_type)
        return self.foundry.search_objects(  # type: ignore[union-attr]
            self.ontology,
            object_type,
            search_body,
        )

    def register_local_asset(self, asset: DigitalTwinAsset) -> None:
        """Register a strictly synthetic local twin asset."""
        self._reject_actuator_metadata(asdict(asset))
        self.twin.register_asset(asset)

    def stage_simulation_action(
        self,
        action: str,
        parameters: dict[str, Any],
        *,
        approved_by_human: bool,
    ) -> dict[str, Any]:
        """Build a reviewable Palantir action request without executing it.

        This deliberately does not call FoundryClient.apply_action. The output
        can be used by an authorized Palantir-side workflow configured for
        staged writes / human review.
        """
        if action not in SAFE_STAGED_ACTIONS:
            raise SafetyViolation(f"action is not in the ZYRAPALANTIR simulation allowlist: {action}")
        if not approved_by_human:
            raise SafetyViolation("human approval is required before staging a simulation action")
        self._reject_actuator_metadata(parameters)
        if parameters.get("synthetic") is not True:
            raise SafetyViolation("staged actions must explicitly declare synthetic=true")
        if not self.ontology:
            raise SafetyViolation("ZYRAPALANTIR_ONTOLOGY must identify the simulation ontology")

        return {
            "kind": "zyrapalantir.staged-simulation-action",
            "ontology": self.ontology,
            "action": action,
            "parameters": parameters,
            "execution": "NOT_EXECUTED_BY_BACKBONE",
            "review": "HUMAN_REQUIRED",
            "outbound_actuation": False,
        }

    def _require_foundry(self) -> None:
        if self.foundry is None:
            raise SafetyViolation("Palantir Foundry is not configured for this runtime")
        if not self.ontology:
            raise SafetyViolation("ZYRAPALANTIR_ONTOLOGY is not configured")

    @staticmethod
    def _require_simulation_object_type(object_type: str) -> None:
        if object_type not in SIMULATION_OBJECT_TYPES:
            raise SafetyViolation(f"object type is outside the ZYRAPALANTIR simulation ontology: {object_type}")

    @staticmethod
    def _reject_actuator_metadata(value: Any) -> None:
        """Reject payloads that attempt to smuggle real-control coordinates."""
        forbidden = {
            "plc",
            "scada",
            "modbus",
            "dnp3",
            "bacnet",
            "opcua",
            "opc-ua",
            "controller_ip",
            "device_ip",
            "actuator_endpoint",
            "real_endpoint",
            "credential",
            "password",
            "api_key",
            "token",
        }

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, child in node.items():
                    if str(key).strip().lower() in forbidden:
                        raise SafetyViolation(f"real-control metadata is prohibited: {key}")
                    walk(child)
            elif isinstance(node, (list, tuple, set)):
                for child in node:
                    walk(child)

        walk(value)
