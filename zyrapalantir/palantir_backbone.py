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
}


@dataclass(frozen=True)
class FoundryBackboneConfig:
    ontology_rid: str = "ri.ontology.main.ontology.zyrapalantir"
    object_prefix: str = "Zyra"
    simulation_action_type: str = "ZyraSimulateResponseAction"


class ZyraPalantirFoundryBackbone:
    """Read/write adapter between ZYRAPALANTIR state and Foundry-like objects.

    The adapter intentionally exposes only synthetic object materialization and
    simulation staging. It does not grant generic Foundry action execution.
    """

    def __init__(
        self,
        *,
        client: Optional[FoundryClient] = None,
        config: Optional[FoundryBackboneConfig] = None,
    ) -> None:
        self.client = client or FoundryClient()
        self.config = config or FoundryBackboneConfig()

    def _configured(self) -> bool:
        token = os.environ.get("PALANTIR_TOKEN") or os.environ.get("FOUNDRY_TOKEN")
        host = os.environ.get("PALANTIR_FOUNDRY_URL") or os.environ.get("FOUNDRY_URL")
        return bool(token and host)

    def materialize_asset(self, asset: DigitalTwinAsset) -> dict[str, Any]:
        return {
            "objectType": "ZyraDigitalTwinAsset",
            "primaryKey": asset.asset_id,
            "properties": asdict(asset),
            "synthetic": True,
            "ontologyRid": self.config.ontology_rid,
        }

    def materialize_state(self, state: ZyraPalantir) -> list[dict[str, Any]]:
        return [self.materialize_asset(asset) for asset in state.assets.values()]

    def stage_simulation_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if action.get("actionType") != self.config.simulation_action_type:
            raise SafetyViolation("only the synthetic simulation action type may be staged")
        return {
            "status": "staged_for_review",
            "configured": self._configured(),
            "action": action,
            "external_mutation_executed": False,
        }

    def status(self) -> dict[str, Any]:
        return {
            "configured": self._configured(),
            "ontology_rid": self.config.ontology_rid,
            "allowed_object_types": sorted(SIMULATION_OBJECT_TYPES),
            "simulation_action_type": self.config.simulation_action_type,
            "arbitrary_action_execution": False,
        }
