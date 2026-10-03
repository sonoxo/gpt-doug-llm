from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from .models import OntologyObject


@dataclass(frozen=True)
class PalantirObjectType:
    api_name: str
    primary_key: str = "id"


TYPE_MAP: Dict[str, PalantirObjectType] = {
    "Platform": PalantirObjectType("zyra_platform"),
    "Subsystem": PalantirObjectType("zyra_subsystem"),
    "Sensor": PalantirObjectType("zyra_sensor"),
    "Observation": PalantirObjectType("zyra_observation"),
    "Track": PalantirObjectType("zyra_track"),
    "Mission": PalantirObjectType("zyra_mission"),
    "Unit": PalantirObjectType("zyra_unit"),
    "Command": PalantirObjectType("zyra_command"),
    "SimulationRun": PalantirObjectType("zyra_simulation_run"),
    "AutonomyAgent": PalantirObjectType("zyra_autonomy_agent"),
    "SafetyConstraint": PalantirObjectType("zyra_safety_constraint"),
    "HumanAuthority": PalantirObjectType("zyra_human_authority"),
    "SimulatedTarget": PalantirObjectType("zyra_simulated_target"),
    "WeaponSystemModel": PalantirObjectType("zyra_weapon_system_model"),
    "RulesOfEngagement": PalantirObjectType("zyra_rules_of_engagement"),
    "EngagementRecommendation": PalantirObjectType("zyra_engagement_recommendation"),
    "AuthorizationRequest": PalantirObjectType("zyra_authorization_request"),
    "HumanAuthorization": PalantirObjectType("zyra_human_authorization"),
    "EffectSimulation": PalantirObjectType("zyra_effect_simulation"),
    "ProtectedEntity": PalantirObjectType("zyra_protected_entity"),
    "NoFireZone": PalantirObjectType("zyra_no_fire_zone"),
    "AuditEvent": PalantirObjectType("zyra_audit_event"),
}


class PalantirOntologyAdapter:
    """Transforms local objects into write payloads for a Palantir integration layer.

    No network call is implemented here; credentials and Foundry-specific APIs stay
    outside the core simulation package.
    """

    def to_write_payload(self, obj: OntologyObject) -> Dict[str, Any]:
        obj_type = obj.__class__.__name__
        if obj_type not in TYPE_MAP:
            raise KeyError(f"No Palantir object type mapping for {obj_type}")
        return {
            "objectType": TYPE_MAP[obj_type].api_name,
            "primaryKey": obj.id,
            "properties": obj.to_dict(),
        }

    def batch(self, objects: Iterable[OntologyObject]) -> List[Dict[str, Any]]:
        return [self.to_write_payload(obj) for obj in objects]
