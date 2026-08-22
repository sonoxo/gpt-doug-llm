#!/usr/bin/env python3
"""ZYRA Protective Order: defensive-only mission policy.

This module is intentionally non-weaponized. It permits protective software
engineering, monitoring, containment, recovery, audit, access control, and
emergency-stop workflows while rejecting weapon control, targeting, destructive
action, offensive exploitation, covert persistence, and safeguard bypass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


BLOCKED_TERMS = {
    "weapon control",
    "weapons control",
    "nuclear launch",
    "missile launch",
    "target acquisition",
    "fire control",
    "kill switch people",
    "autonomous attack",
    "attack target",
    "explosive trigger",
    "detonator",
    "bypass safeguards",
    "override all safeguards",
    "disable safety",
    "covert persistence",
    "sleeper weapon",
}

ALLOWED_DEFENSIVE_DOMAINS = {
    "access control",
    "authentication",
    "authorization",
    "audit logging",
    "backup",
    "containment",
    "data integrity",
    "disaster recovery",
    "emergency stop",
    "incident response",
    "intrusion detection",
    "malware analysis",
    "monitoring",
    "rate limiting",
    "rollback",
    "sandboxing",
    "security testing",
    "tamper detection",
    "threat detection",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    matched_terms: tuple[str, ...] = ()


class ProtectiveOrder:
    VERSION = "PROTECTIVE-ORDER/1.0"

    def evaluate(self, goal: str) -> PolicyDecision:
        text = " ".join(goal.lower().split())
        matched = tuple(sorted(term for term in BLOCKED_TERMS if term in text))
        if matched:
            return PolicyDecision(
                allowed=False,
                reason="Mission requests weapon/destructive control or safeguard bypass; defensive-only policy blocks execution.",
                matched_terms=matched,
            )
        return PolicyDecision(
            allowed=True,
            reason="Mission is eligible for defensive software execution inside existing repository safety boundaries.",
        )

    def require_allowed(self, goal: str) -> None:
        decision = self.evaluate(goal)
        if not decision.allowed:
            terms = ", ".join(decision.matched_terms) or "blocked capability"
            raise PermissionError(f"Protective Order denied mission ({terms}): {decision.reason}")


def describe_capabilities() -> dict[str, object]:
    return {
        "version": ProtectiveOrder.VERSION,
        "mode": "defensive-only",
        "allows": sorted(ALLOWED_DEFENSIVE_DOMAINS),
        "blocks": [
            "weapon control",
            "targeting/attack execution",
            "destructive triggers",
            "offensive exploitation",
            "covert persistence",
            "safeguard bypass",
        ],
        "operator_control": True,
        "emergency_stop": True,
        "no_rebellion": True,
    }
