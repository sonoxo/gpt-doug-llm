from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    OFFICER = "OFFICER"
    CPR = "CPR"
    ADMIN = "ADMIN"
    LLM = "LLM"
    MAX = "MAX"


class TrustState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    VERIFIED = "VERIFIED"
    APPOINTED = "APPOINTED"
    BLACKHOUSE = "BLACKHOUSE"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class AgentCandidate:
    agent_id: str
    name: str
    version: str
    fingerprint: str
    capabilities: list[str]
    test_score: float
    provenance_score: float
    integrity_score: float
    trust_state: str = TrustState.QUARANTINED.value
    source_path: str = ""
    observed_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Appointment:
    appointment_id: str
    agent_id: str
    role: str
    confidence: float
    score: float
    reasons: list[str]
    recommended_permissions: list[str]
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActionProposal:
    action_id: str
    action_type: str
    subject: str
    risk: str
    rationale: list[str]
    requires_approval: bool
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
