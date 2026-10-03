from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StateSnapshot:
    version: str
    objects: Dict[str, Any]


@dataclass
class ProposedTransition:
    transition_id: str
    actor: str
    changes: Dict[str, Any]
    required_policy: str
    requires_human_approval: bool = True


@dataclass
class CounterfactualBranch:
    branch_id: str
    base_version: str
    objects: Dict[str, Any]


@dataclass
class SimulationResult:
    allowed: bool
    reasons: List[str]
    expected_state: Dict[str, Any]


@dataclass
class ReconciliationResult:
    decision: str
    drift: Dict[str, Any]


@dataclass
class TransactionResult:
    status: str
    branch_id: Optional[str] = None
    reason: Optional[str] = None
