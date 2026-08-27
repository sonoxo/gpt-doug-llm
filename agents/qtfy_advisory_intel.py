"""Defensive intelligence profile for JCSA-20260826-01.

Source: FBI/NSA/CNMF joint Cybersecurity Advisory published 2026-08-26.
The advisory is TLP:CLEAR. This module preserves a defensive-only interpretation:
IOC matches are leads to investigate and vet, not automatic authorization to block,
hack back, or take action against third-party infrastructure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agents.adaptive_intelligence import Evidence
from agents.qtfy_ontology import build_defensive_ontology
from agents.va3lm_infrastructure_shield import build_infrastructure_shield_plan

ADVISORY_ID = "JCSA-20260826-01"
ADVISORY_URL = "https://www.ic3.gov/CSA/2026/260826.pdf"
IOC_FILES_URL = "https://www.ic3.gov/CSA/2026/QTFY_IOC_Files.csv"
IOC_INFRASTRUCTURE_URL = "https://www.ic3.gov/CSA/2026/QTFY_IOC_Infrastructure.csv"
TLP = "TLP:CLEAR"
PUBLISHED = "2026-08-26"
THREAT_LABEL = "QTFY"
ONTOLOGY_CONTRACT_PATH = "foundry/ontology/qtfy-defense-ontology.json"

ATTACK_TECHNIQUES = {
    "T1595.002": "Active Scanning: Vulnerability Scanning",
    "T1190": "Exploit Public-Facing Application",
    "T1505.003": "Server Software Component: Web Shell",
    "T1583.003": "Acquire Infrastructure: Virtual Private Server",
    "T1587": "Develop Capabilities",
}

KEY_ACTIONS = (
    "Apply the latest software and firmware updates to organizational devices.",
    "Protect operational information from unintentional disclosure via internet-facing applications.",
    "Isolate critical systems from edge devices using zero-trust segmentation principles.",
    "Hunt for advisory indicators of compromise and establish network-activity baselines.",
)

INCIDENT_RESPONSE = (
    "Identify compromised hosts and isolate or quarantine them.",
    "Threat hunt to scope the intrusion using logs, artifacts, devices, accounts, and timeline evidence.",
    "Report confirmed or suspected compromise to the FBI and other appropriate agencies.",
    "Collect enough evidence to select effective eviction countermeasures, then contain and eradicate the actor.",
    "Harden the environment to reduce recurrence.",
)

CONTROL_VALIDATION = (
    "Select an ATT&CK technique from the advisory.",
    "Align existing security technologies against that technique.",
    "Test the technologies against the technique in an authorized environment.",
    "Analyze detection and prevention performance.",
    "Repeat across security technologies to build performance evidence.",
    "Tune people, processes, and technologies using the measured results.",
)

TARGET_SECTORS = (
    "Government Services and Facilities",
    "Defense Industrial Base",
    "Communications",
    "Energy",
    "Information Technology",
    "Water and Wastewater Systems",
)


@dataclass(frozen=True)
class AdvisoryControl:
    control_id: str
    objective: str
    va3lm_lane: str
    evidence_required: str


CONTROLS = (
    AdvisoryControl("QTFY-PATCH", "Patch software/firmware and identify end-of-support devices.", "agent-inventory", "patch-and-lifecycle-evidence"),
    AdvisoryControl("QTFY-SECRETS", "Audit public-facing apps for exposed secrets and sensitive configuration.", "agent-identity", "secret-exposure-review"),
    AdvisoryControl("QTFY-SEGMENT", "Isolate critical systems from edge devices with zero-trust segmentation.", "agent-segmentation", "segmentation-policy-evidence"),
    AdvisoryControl("QTFY-HUNT", "Hunt advisory IOCs and ATT&CK behaviors across authorized telemetry.", "agent-detection", "hunt-query-and-result-evidence"),
    AdvisoryControl("QTFY-CONTAIN", "Quarantine confirmed compromised assets and revoke compromised access.", "agent-containment", "containment-evidence"),
    AdvisoryControl("QTFY-RECOVER", "Restore hardened known-good service and validate recovery.", "agent-recovery", "recovery-validation-evidence"),
    AdvisoryControl("QTFY-VERIFY", "Exercise and validate controls against the advisory's ATT&CK techniques.", "agent-verify", "control-performance-report"),
)


def advisory_evidence() -> tuple[Evidence, ...]:
    """Return source-aware evidence records suitable for ``AdaptiveIntel.absorb``."""
    statements = (
        "FBI, NSA, and CNMF published JCSA-20260826-01 on August 26, 2026 and marked it TLP:CLEAR.",
        "The advisory describes China-linked QTFY activity targeting U.S. and foreign organizations, including critical infrastructure.",
        "The advisory's key actions are patching, protecting operational information, isolating critical systems from edge devices, and hunting IOCs.",
        "The advisory maps QTFY behavior to MITRE ATT&CK techniques including T1595.002, T1190, T1505.003, T1583.003, and T1587.",
        "The advisory instructs organizations to investigate or vet listed IP indicators before taking actions such as blocking.",
        "The advisory recommends continuously exercising, testing, and tuning security controls against the mapped ATT&CK techniques.",
    )
    return tuple(
        Evidence(
            source_id=f"{ADVISORY_ID}:{index}",
            text=text,
            provenance=ADVISORY_URL,
            reliability=0.99,
            corroboration=1,
        )
        for index, text in enumerate(statements, start=1)
    )


def ioc_action_policy(*, indicator_match: bool, corroborated: bool = False) -> dict[str, Any]:
    """Apply the advisory's caution: an IOC match is a hunting lead, not auto-block authority."""
    if not indicator_match:
        return {"matched": False, "action": "none", "humanReviewRequired": False}
    return {
        "matched": True,
        "action": "investigate-and-vet",
        "corroborated": bool(corroborated),
        "autoBlock": False,
        "humanReviewRequired": True,
        "reason": "JCSA-20260826-01 recommends investigating or vetting indicators prior to actions such as blocking.",
    }


def build_qtfy_defensive_plan() -> dict[str, Any]:
    """Adapt the VA3LM Infrastructure Shield and intelligence ontology to QTFY."""
    shield = build_infrastructure_shield_plan(severity="critical")
    control_records = [asdict(control) for control in CONTROLS]
    ioc_feeds = [IOC_FILES_URL, IOC_INFRASTRUCTURE_URL]
    ontology = build_defensive_ontology(
        advisory_id=ADVISORY_ID,
        advisory_url=ADVISORY_URL,
        threat_label=THREAT_LABEL,
        tlp=TLP,
        published=PUBLISHED,
        techniques=ATTACK_TECHNIQUES,
        controls=control_records,
        target_sectors=TARGET_SECTORS,
        ioc_feeds=ioc_feeds,
    )
    return {
        "advisoryId": ADVISORY_ID,
        "source": ADVISORY_URL,
        "tlp": TLP,
        "published": PUBLISHED,
        "threat": THREAT_LABEL,
        "mission": "DEFEND_AUTHORIZED_ENVIRONMENTS_AGAINST_QTFY_TTPS",
        "mode": "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "targetSectors": list(TARGET_SECTORS),
        "attackTechniques": dict(ATTACK_TECHNIQUES),
        "keyActions": list(KEY_ACTIONS),
        "incidentResponse": list(INCIDENT_RESPONSE),
        "controlValidation": list(CONTROL_VALIDATION),
        "controls": control_records,
        "iocFeeds": ioc_feeds,
        "iocPolicy": {
            "default": "investigate-and-vet",
            "automaticBlocking": False,
            "humanReviewRequired": True,
        },
        "ontologyContract": ONTOLOGY_CONTRACT_PATH,
        "ontology": ontology,
        "shield": shield,
        "stopWhenAll": [
            "qtfy-hunt-complete",
            "exposed-edge-risk-reviewed",
            "critical-segmentation-verified",
            "compromise-contained-if-present",
            "recovery-validated-if-required",
            "attack-control-tests-recorded",
            "evidence-recorded",
        ],
    }
