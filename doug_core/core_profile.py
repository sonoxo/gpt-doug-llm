from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CoreProfile:
    name: str
    version: str
    signal_word: str
    capability_state_model: tuple[str, ...]
    truth_labels: tuple[str, ...]
    max_same_failure_retries: int
    local_first: bool
    human_authority_required: bool
    proof_required_for_verified: bool
    safe_domains: tuple[str, ...]
    prohibited_operational_domains: tuple[str, ...]


GPT_DOUG_MAX_PROFILE: Final[CoreProfile] = CoreProfile(
    name="GPT-DOUG-MAX",
    version="2026.08-core.1",
    signal_word="EUREKA",
    capability_state_model=("PLANNED", "IMPLEMENTED", "TESTED", "VERIFIED"),
    truth_labels=(
        "FACT",
        "INFERENCE",
        "PREDICTION",
        "SIMULATION",
        "RECOMMENDATION",
        "UNKNOWN",
    ),
    max_same_failure_retries=3,
    local_first=True,
    human_authority_required=True,
    proof_required_for_verified=True,
    safe_domains=(
        "software engineering",
        "local orchestration",
        "defensive cyber security",
        "mission assurance",
        "service resilience",
        "maintenance and recovery",
        "public or simulated awareness",
        "non-weaponized UAV readiness",
        "synthetic-data training",
        "human-governed decision support",
    ),
    prohibited_operational_domains=(
        "real-world target designation",
        "weapon aiming",
        "ballistic firing solutions",
        "fire-control computation",
        "strike planning",
        "weapon allocation",
        "weapon release",
        "firing-relay or effector control",
        "autonomous lethal execution",
        "weaponized UAV payload control",
        "offensive cyber operations",
    ),
)


def get_core_profile() -> CoreProfile:
    """Return the immutable runtime identity and governance profile."""
    return GPT_DOUG_MAX_PROFILE


def can_mark_verified(*, implemented: bool, tested: bool, exit_zero: bool, observed: bool, proof_persisted: bool) -> bool:
    """Truth gate for VERIFIED capability status."""
    return all((implemented, tested, exit_zero, observed, proof_persisted))
