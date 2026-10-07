from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    matched: List[str]
    reason: str


_BLOCK_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("autonomous_target_selection", ("autonomous target selection", "target selection")),
    ("weapons_release", ("weapons release", "weapon release", "fire weapon")),
    ("weapon_or_drone_swarm_control", ("weapon swarm control", "drone swarm control", "armed drone swarm")),
    ("hostile_engagement", ("hostile engagement", "engage hostile", "attack target")),
    ("critical_infrastructure_disruption", ("critical infrastructure disruption", "disrupt power grid", "disable water system")),
    ("hack_back", ("hack back", "counter hack", "retaliatory hacking")),
    ("credential_theft", ("credential theft", "steal credentials", "dump passwords")),
    ("unattended_real_world_vehicle_control", ("unattended real world vehicle", "unattended vehicle control")),
    ("implant_control", ("implant control", "control implant")),
    ("destructive_biological_or_cyber_actuation", ("destructive biological actuation", "destructive cyber actuation")),
    ("bypass_human_authorization", ("bypass human authorization", "ignore human approval")),
)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().replace("-", " ").replace("_", " ").split())


def evaluate_request(text: str) -> PolicyDecision:
    normalized = _normalize(text)
    matched = []
    for action, patterns in _BLOCK_PATTERNS:
        if any(_normalize(pattern) in normalized for pattern in patterns):
            matched.append(action)
    if matched:
        return PolicyDecision(
            decision="BLOCK",
            matched=sorted(set(matched)),
            reason="Request crosses GoDsEye read-only safety boundaries.",
        )
    return PolicyDecision(
        decision="ALLOW_READ_ONLY",
        matched=[],
        reason="Request is within read-only observation, analysis, planning, or simulation scope.",
    )
