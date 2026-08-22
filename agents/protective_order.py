from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProtectiveOrder:
    """Non-destructive defensive policy for ZYRA agentic operation."""

    name: str = "ZYRA_PROTECTIVE_ORDER"
    version: str = "1.0"
    human_authority_required: bool = True
    emergency_shutdown_required: bool = True
    rollback_required: bool = True
    audit_required: bool = True
    repository_scope_required: bool = True
    destructive_external_control: bool = False
    weapon_control: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROTECTIVE_ORDER = ProtectiveOrder()


BLOCKED_CAPABILITIES = frozenset({
    "weapon_control",
    "targeting",
    "launch_control",
    "detonation_control",
    "destructive_external_control",
    "credential_theft",
    "malware_deployment",
    "safety_bypass",
    "disable_rollback",
    "disable_human_shutdown",
})


ALLOWED_DEFENSIVE_CAPABILITIES = frozenset({
    "repository_read",
    "repository_write",
    "code_generation",
    "test_execution",
    "linting",
    "static_analysis",
    "checkpoint",
    "rollback",
    "audit_logging",
    "dependency_review",
    "configuration_validation",
    "sandboxed_build",
    "emergency_shutdown",
    "operator_authorization",
})


def authorize_capability(capability: str) -> dict[str, Any]:
    name = str(capability or "").strip().lower()
    if not name:
        return {"allowed": False, "reason": "capability is required"}
    if name in BLOCKED_CAPABILITIES:
        return {
            "allowed": False,
            "capability": name,
            "reason": "blocked by non-bypassable protective order",
        }
    if name in ALLOWED_DEFENSIVE_CAPABILITIES:
        return {
            "allowed": True,
            "capability": name,
            "reason": "allowed defensive engineering capability",
        }
    return {
        "allowed": False,
        "capability": name,
        "reason": "capability is not allowlisted",
    }


def status() -> dict[str, Any]:
    return {
        "policy": PROTECTIVE_ORDER.to_dict(),
        "blocked_capabilities": sorted(BLOCKED_CAPABILITIES),
        "allowed_defensive_capabilities": sorted(ALLOWED_DEFENSIVE_CAPABILITIES),
        "mode": "DEFENSIVE_ONLY",
    }
