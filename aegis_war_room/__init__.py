"""AEGIS War Room: bounded, non-lethal decision support for mission assurance.

This package is intentionally limited to defensive, logistical, resilience,
continuity, maintenance, evacuation, communications, cyber-defense, and
humanitarian decision support. It does not perform targeting, fire control,
weapon release, strike planning, lethal engagement, or offensive cyber actions.
"""

from .engine import DecisionEngine, DecisionRejected
from .models import (
    DecisionCategory,
    DecisionOption,
    DecisionRequest,
    DecisionResult,
    EvidenceItem,
    RiskLevel,
)

__all__ = [
    "DecisionEngine",
    "DecisionRejected",
    "DecisionCategory",
    "DecisionOption",
    "DecisionRequest",
    "DecisionResult",
    "EvidenceItem",
    "RiskLevel",
]
