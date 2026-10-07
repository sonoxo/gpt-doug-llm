from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SubsystemState:
    name: str
    status: str
    generated_at: Optional[str] = None
    source_count: Optional[int] = None
    stale: bool = False
    partial: bool = False
    provenance: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoDsEyeSnapshot:
    schema: str
    generated_at: str
    policy: Dict[str, Any]
    subsystems: Dict[str, SubsystemState]
    provenance: List[str] = field(default_factory=list)
    uncertainty: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "policy": dict(self.policy),
            "subsystems": {name: state.to_dict() for name, state in self.subsystems.items()},
            "provenance": list(self.provenance),
            "uncertainty": list(self.uncertainty),
        }
