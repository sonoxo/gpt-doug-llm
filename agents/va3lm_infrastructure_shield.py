"""VA3LM U.S. infrastructure protection orchestration contract.

Defensive-only control-plane primitives for protecting authorized U.S. data and
critical-infrastructure environments. This module intentionally excludes offensive
operations against third-party systems. "Active defense" is limited to containment,
decoys, honeypots, adversary emulation in owned ranges, credential isolation, and
recovery actions inside explicitly authorized environments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any, Iterable

SHIELD_COMMAND = "/VA3LM-INFRA-SHIELD"
SHIELD_PROFILE = "GPT-DOUG-LLM-VIRGINIA-STATEOFEMERGENCY-PALANTIR-DEFENSE-OFFENSE-DEFENSE"


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class DefensiveLane:
    name: str
    responsibility: str
    authorized_actions: tuple[str, ...]
    evidence: str


LANES: tuple[DefensiveLane, ...] = (
    DefensiveLane(
        "agent-inventory",
        "Maintain signed inventories and dependency graphs for authorized IT, cloud, API, data, identity, and OT assets.",
        ("inventory", "classify", "dependency-map", "exposure-check"),
        "asset-and-dependency-evidence",
    ),
    DefensiveLane(
        "agent-identity",
        "Reduce identity blast radius with phishing-resistant MFA, workload identity, least privilege, and rapid credential revocation.",
        ("risk-score", "disable-compromised-credential", "rotate-secret", "require-step-up-auth"),
        "identity-control-evidence",
    ),
    DefensiveLane(
        "agent-segmentation",
        "Protect critical zones by enforcing deny-by-default segmentation and removing direct internet exposure from sensitive OT/management planes.",
        ("isolate-workload", "restrict-ingress", "restrict-egress", "quarantine-zone"),
        "network-policy-evidence",
    ),
    DefensiveLane(
        "agent-detection",
        "Correlate authorized telemetry into incidents without creating a centralized raw-data surveillance store.",
        ("detect", "correlate", "prioritize", "open-incident"),
        "incident-evidence",
    ),
    DefensiveLane(
        "agent-containment",
        "Contain compromise inside authorized infrastructure using isolation, blocks, decoys, and owned cyber-range adversary emulation.",
        ("block-indicator", "isolate-host", "disable-session", "deploy-decoy", "range-emulation"),
        "containment-evidence",
    ),
    DefensiveLane(
        "agent-recovery",
        "Restore critical services from known-good state using immutable backups, golden images, key rotation, and clean-room validation.",
        ("restore", "rotate-keys", "validate-backup", "rebuild-from-golden-image", "verify-service"),
        "recovery-evidence",
    ),
    DefensiveLane(
        "agent-verify",
        "Require explicit evidence before declaring an incident contained or recovered.",
        ("verify-controls", "verify-logs", "verify-recovery", "issue-final-report"),
        "verification-report",
    ),
)

PROHIBITED_ACTIONS = (
    "unauthorized access to third-party systems",
    "credential theft",
    "malware deployment",
    "destructive payloads",
    "denial-of-service attacks",
    "data exfiltration",
    "offensive persistence outside owned infrastructure",
    "autonomous physical-force or weapon targeting",
)

STOP_CONDITIONS = (
    "critical-services-operational",
    "compromise-contained",
    "privileged-credentials-rotated",
    "known-vulnerable-paths-mitigated",
    "recovery-validated",
    "evidence-recorded",
)


def normalize_severity(value: str | int | Severity) -> Severity:
    if isinstance(value, Severity):
        return value
    if isinstance(value, int):
        return Severity(max(int(Severity.INFO), min(int(Severity.CRITICAL), value)))
    lookup = {
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
        "critical": Severity.CRITICAL,
    }
    try:
        return lookup[value.strip().lower()]
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"unknown severity: {value!r}") from exc


def required_controls(severity: str | int | Severity) -> tuple[str, ...]:
    level = normalize_severity(severity)
    controls = ["inventory-evidence", "immutable-audit-log", "human-review-path"]
    if level >= Severity.MEDIUM:
        controls += ["least-privilege-check", "network-segmentation-check", "backup-integrity-check"]
    if level >= Severity.HIGH:
        controls += ["credential-rotation-plan", "containment-plan", "clean-recovery-plan"]
    if level >= Severity.CRITICAL:
        controls += ["incident-command-activation", "out-of-band-communications", "continuity-of-operations-check"]
    return tuple(controls)


def completion_evidence(evidence: Iterable[str]) -> dict[str, Any]:
    supplied = {item.strip() for item in evidence if item and item.strip()}
    missing = [condition for condition in STOP_CONDITIONS if condition not in supplied]
    return {
        "complete": not missing,
        "missing": missing,
        "required": list(STOP_CONDITIONS),
    }


def build_infrastructure_shield_plan(*, severity: str | int | Severity = Severity.HIGH) -> dict[str, Any]:
    level = normalize_severity(severity)
    return {
        "command": SHIELD_COMMAND,
        "profile": SHIELD_PROFILE,
        "mission": "PROTECT_US_DATA_AND_CRITICAL_INFRASTRUCTURE",
        "mode": "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "framework": ["GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"],
        "severity": level.name,
        "controlGates": list(required_controls(level)),
        "lanes": [asdict(lane) for lane in LANES],
        "federation": {
            "rawDataDefault": "remain-with-owner",
            "sharedData": ["indicators", "attack-patterns", "exposure-status", "incident-metadata", "recovery-status"],
            "nationalKillSwitch": False,
            "localOperationalAuthority": True,
        },
        "activeDefenseBoundary": "containment-decoys-honeypots-and-owned-cyber-range-only",
        "prohibitedActions": list(PROHIBITED_ACTIONS),
        "stopWhenAll": list(STOP_CONDITIONS),
    }
