from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class DecisionCategory(str, Enum):
    MISSION_CONTINUITY = "mission_continuity"
    LOGISTICS = "logistics"
    MAINTENANCE = "maintenance"
    EVACUATION = "evacuation"
    HUMANITARIAN = "humanitarian"
    COMMUNICATIONS_RESILIENCE = "communications_resilience"
    CYBER_DEFENSE = "cyber_defense"
    INFRASTRUCTURE_RECOVERY = "infrastructure_recovery"
    PERSONNEL_SAFETY = "personnel_safety"
    RESOURCE_ALLOCATION = "resource_allocation"

    # Explicitly represented so the engine can fail closed.
    TARGET_SELECTION = "target_selection"
    WEAPON_RELEASE = "weapon_release"
    FIRE_CONTROL = "fire_control"
    STRIKE_PLANNING = "strike_planning"
    LETHAL_ENGAGEMENT = "lethal_engagement"
    OFFENSIVE_CYBER = "offensive_cyber"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source: str
    summary: str
    confidence: float
    timestamp: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class DecisionOption:
    option_id: str
    title: str
    description: str
    personnel_safety: float
    civilian_safety: float
    mission_continuity: float
    resilience: float
    reversibility: float
    policy_fit: float
    logistics_feasibility: float
    cost_efficiency: float
    recovery_speed: float
    evidence_ids: Sequence[str] = field(default_factory=tuple)
    assumptions: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "personnel_safety",
            "civilian_safety",
            "mission_continuity",
            "resilience",
            "reversibility",
            "policy_fit",
            "logistics_feasibility",
            "cost_efficiency",
            "recovery_speed",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class DecisionRequest:
    request_id: str
    mission_id: str
    principal_id: str
    category: DecisionCategory
    objective: str
    environment: str
    options: Sequence[DecisionOption]
    evidence: Sequence[EvidenceItem] = field(default_factory=tuple)
    constraints: Mapping[str, str] = field(default_factory=dict)
    human_approval_required: bool = True


@dataclass(frozen=True)
class RankedOption:
    option_id: str
    score: float
    confidence: float
    rationale: Sequence[str]
    evidence_ids: Sequence[str]


@dataclass(frozen=True)
class DecisionResult:
    request_id: str
    status: str
    category: DecisionCategory
    ranked_options: Sequence[RankedOption]
    recommended_option_id: str | None
    requires_human_approval: bool
    risk_level: RiskLevel
    limitations: Sequence[str]
    provenance: Mapping[str, str]
