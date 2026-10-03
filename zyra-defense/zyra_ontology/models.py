from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Classification(str, Enum):
    UNKNOWN = "unknown"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SIMULATED_ADVERSARY = "simulated_adversary"
    PROTECTED = "protected"


class AuthorizationDecision(str, Enum):
    APPROVE_SIMULATION = "approve_simulation"
    DENY = "deny"


@dataclass(slots=True)
class OntologyObject:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = self.__class__.__name__
        return data


@dataclass(slots=True)
class Platform(OntologyObject):
    name: str = ""
    domain: str = "air"
    simulated: bool = True


@dataclass(slots=True)
class Subsystem(OntologyObject):
    platform_id: str = ""
    name: str = ""


@dataclass(slots=True)
class Sensor(OntologyObject):
    platform_id: str = ""
    name: str = ""
    modality: str = "synthetic"


@dataclass(slots=True)
class Observation(OntologyObject):
    sensor_id: str = ""
    source: str = "synthetic"
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Track(OntologyObject):
    label: str = ""
    classification: Classification = Classification.UNKNOWN
    confidence: float = 0.0
    simulated: bool = True
    observation_ids: List[str] = field(default_factory=list)


@dataclass(slots=True)
class Mission(OntologyObject):
    name: str = ""
    purpose: str = "training"
    simulation_only: bool = True


@dataclass(slots=True)
class Unit(OntologyObject):
    name: str = ""
    simulated: bool = True


@dataclass(slots=True)
class Command(OntologyObject):
    mission_id: str = ""
    text: str = ""
    executable: bool = False


@dataclass(slots=True)
class SimulationRun(OntologyObject):
    mission_id: str = ""
    status: str = "created"
    event_ids: List[str] = field(default_factory=list)


@dataclass(slots=True)
class AutonomyAgent(OntologyObject):
    name: str = "ZYRA"
    advisory_only: bool = True


@dataclass(slots=True)
class SafetyConstraint(OntologyObject):
    name: str = ""
    rule: str = ""
    hard_block: bool = True


@dataclass(slots=True)
class HumanAuthority(OntologyObject):
    display_name: str = "human-controller"
    role: str = "simulation_authority"


@dataclass(slots=True)
class SimulatedTarget(OntologyObject):
    track_id: str = ""
    label: str = ""
    synthetic: bool = True


@dataclass(slots=True)
class WeaponSystemModel(OntologyObject):
    name: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    simulation_only: bool = True
    has_actuation_interface: bool = False


@dataclass(slots=True)
class RulesOfEngagement(OntologyObject):
    name: str = "simulation-roe"
    clauses: List[str] = field(default_factory=list)
    simulation_only: bool = True


@dataclass(slots=True)
class EngagementRecommendation(OntologyObject):
    mission_id: str = ""
    simulated_target_id: str = ""
    weapon_system_model_id: Optional[str] = None
    recommendation: str = "observe"
    rationale: str = ""
    confidence: float = 0.0
    advisory_only: bool = True


@dataclass(slots=True)
class AuthorizationRequest(OntologyObject):
    recommendation_id: str = ""
    requested_action: str = "run_simulated_effect"
    simulation_only: bool = True


@dataclass(slots=True)
class HumanAuthorization(OntologyObject):
    request_id: str = ""
    authority_id: str = ""
    decision: AuthorizationDecision = AuthorizationDecision.DENY
    reason: str = ""


@dataclass(slots=True)
class EffectSimulation(OntologyObject):
    recommendation_id: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    synthetic: bool = True


@dataclass(slots=True)
class ProtectedEntity(OntologyObject):
    label: str = ""
    reason: str = "protected"


@dataclass(slots=True)
class NoFireZone(OntologyObject):
    label: str = ""
    geometry_ref: str = "synthetic-zone"


@dataclass(slots=True)
class AuditEvent(OntologyObject):
    actor: str = "system"
    action: str = ""
    object_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
