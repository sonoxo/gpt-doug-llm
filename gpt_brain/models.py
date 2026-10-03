from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentSpec:
    name: str
    purpose: str
    system_prompt: str
    weight: float = 1.0


@dataclass
class EvidenceItem:
    source: str
    claim: str
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainResult:
    answer: str
    run_id: str
    agents: list[str]
    ontology_context: list[dict[str, Any]]
    memory_context: list[dict[str, Any]]
    critique: str
    provenance: list[str]
    uncertainty: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
