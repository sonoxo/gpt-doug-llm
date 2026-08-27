"""Defensive intelligence profile for JCSA-20260826-01.

Source: FBI/NSA/CNMF joint Cybersecurity Advisory published 2026-08-26.
The advisory is TLP:CLEAR. This module preserves source provenance and a
defensive-only interpretation: IOC matches are investigative leads, not automatic
authority to block or act against third-party infrastructure.
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
SOURCE_PACK_PATH = "intel/qtfy/JCSA-20260826-01.json"

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
    "Harden the environment to prevent additional malicious activity and validate recovery.",
)

CONTROL_VALIDATION = (
    "Select an ATT&CK technique from the advisory.",
    "Align existing security technologies against the technique.",
    "Test the technologies against the technique in an authorized environment.",
    "Analyze detection and prevention technologies' performance.",
    "Repeat across security technologies to build comprehensive performance evidence.",
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

ORGANIZATIONS = (
    {"id": "nanjing-xinjiuwei", "name": "Nanjing Xinjiuwei Network Technology Co.", "role": "ADVISORY_ATTRIBUTED_ENABLER", "sourcePage": 4},
    {"id": "mss-unit-0718", "name": "Unit 0718", "role": "ADVISORY_MENTIONED_MSS_UNIT", "sourcePage": 5},
    {"id": "mss-unit-9086", "name": "Unit 9086", "role": "ADVISORY_MENTIONED_MSS_UNIT", "sourcePage": 5},
    {"id": "cnitsec-jilin", "name": "CNITSEC Jilin Subcenter", "role": "ADVISORY_MENTIONED_ENTITY", "sourcePage": 5},
    {"id": "bozhi-elextec", "name": "Bozhi Security Technology Co., Ltd. / Elextec Cybersecurity, Inc.", "role": "ADVISORY_MENTIONED_ENTITY", "sourcePage": 5},
    {"id": "cy-tech", "name": "Changyang Technology (Cy-Tech) (Beijing) Co., Ltd.", "role": "ADVISORY_MENTIONED_ENTITY", "sourcePage": 6},
    {"id": "lexbell", "name": "Nanjing Lexbell Information Technology Co., Ltd.", "role": "ADVISORY_MENTIONED_ENTITY", "sourcePage": 6},
    {"id": "fujian-ares", "name": "Fujian Ares Network Technology Co., Ltd.", "role": "ADVISORY_MENTIONED_ENTITY", "sourcePage": 6},
)

THREAT_TOOLS = (
    {"id": "qscan", "name": "QScan", "category": "DISTRIBUTED_SCANNING_AND_EXPLOITATION_PLATFORM", "sourcePage": 8},
    {"id": "qtrouter", "name": "QTRouter", "category": "TRAFFIC_OBFUSCATION_NETWORK", "sourcePage": 9},
    {"id": "proxy-platform-management", "name": "Proxy Platform Management", "category": "BOTNET_MANAGEMENT_PLATFORM", "sourcePage": 10},
    {"id": "proxy-pool-management", "name": "Proxy Pool Management System", "category": "BOTNET_AND_PROXY_AGGREGATOR", "sourcePage": 10},
    {"id": "qtbotnet", "name": "QTBotnet", "category": "BOTNET_CONTROL_PLATFORM", "sourcePage": 10},
)

VULNERABILITIES = (
    {"id": "CVE-2019-11510", "context": "Pulse Secure VPN", "sourcePage": 6},
    {"id": "CVE-2018-13379", "context": "Fortinet FortiOS SSL VPN", "sourcePage": 7},
    {"id": "CVE-2019-19781", "context": "Citrix ADC and Gateway", "sourcePage": 7},
    {"id": "CVE-2021-26855", "context": "Microsoft Exchange ProxyLogon", "sourcePage": 7},
    {"id": "CVE-2020-5902", "context": "F5 BIG-IP", "sourcePage": 7},
    {"id": "CVE-2019-10068", "context": "Kentico CMS", "sourcePage": 7},
    {"id": "CVE-2021-44228", "context": "Log4Shell", "sourcePage": 7},
    {"id": "CVE-2023-22515", "context": "Atlassian Confluence", "sourcePage": 7},
    {"id": "CVE-2024-24919", "context": "Check Point Quantum Gateway", "sourcePage": 7},
    {"id": "CVE-2024-8190", "context": "Ivanti CSA", "sourcePage": 8},
    {"id": "CVE-2024-8963", "context": "Ivanti CSA", "sourcePage": 8},
    {"id": "CVE-2024-9380", "context": "Ivanti CSA", "sourcePage": 8},
    {"id": "CVE-2025-31161", "context": "CrushFTP", "sourcePage": 8},
    {"id": "CVE-2026-1731", "context": "BeyondTrust Remote Support", "sourcePage": 8},
)

CAMPAIGN_EVENTS = (
    {"id": "evt-2018-05-doe", "date": "2018-05", "targetCategory": "US Department of Energy", "activity": "vulnerability scanning", "outcome": "unsuccessful access attempt", "sourcePage": 6},
    {"id": "evt-2019-07-election", "date": "2019-07", "targetCategory": "US election system", "activity": "vulnerability scanning", "outcome": "unsuccessful access attempt", "sourcePage": 6},
    {"id": "evt-2019-08-pulse", "date": "2019-08", "targetCategory": "US federal organizations", "activity": "public-facing VPN exploitation", "outcome": "advisory-observed exploitation activity", "vulnerabilityIds": ["CVE-2019-11510"], "sourcePage": 6},
    {"id": "evt-2020-01-citrix", "date": "2020-01", "targetCategory": "numerous US targets", "activity": "public-facing gateway exploitation", "outcome": "advisory-observed exploitation activity", "vulnerabilityIds": ["CVE-2019-19781"], "sourcePage": 7},
    {"id": "evt-2021-taiwan-energy", "date": "2021", "targetCategory": "Taiwan energy sector", "activity": "remote access trojan installation", "outcome": "systems compromised according to advisory", "sourcePage": 7},
    {"id": "evt-2021-12-log4shell", "date": "2021-12", "targetCategory": "internet-facing systems", "activity": "Log4Shell exploitation", "outcome": "advisory-observed exploitation activity", "vulnerabilityIds": ["CVE-2021-44228"], "sourcePage": 7},
    {"id": "evt-2023-10-confluence", "date": "2023-10", "targetCategory": "Atlassian Confluence systems", "activity": "public-facing application exploitation", "outcome": "advisory-observed exploitation activity", "vulnerabilityIds": ["CVE-2023-22515"], "sourcePage": 7},
    {"id": "evt-2024-05-qscan", "date": "2024-05", "targetCategory": "power and telecommunications organizations", "activity": "QScan scanning and exploitation", "outcome": "advisory reports data exfiltration from more than 300 organizations worldwide", "toolIds": ["qscan"], "vulnerabilityIds": ["CVE-2024-24919"], "sourcePage": 7},
    {"id": "evt-2024-09-ivanti", "date": "2024-09", "targetCategory": "US government and research organizations", "activity": "Ivanti CSA zero-day exploitation", "outcome": "advisory-observed exploitation activity", "vulnerabilityIds": ["CVE-2024-8190", "CVE-2024-8963", "CVE-2024-9380"], "sourcePage": 8},
    {"id": "evt-2026-02-beyondtrust", "date": "2026-02", "targetCategory": "US state government and water district", "activity": "QScan exploitation", "outcome": "advisory-observed targeting", "toolIds": ["qscan"], "vulnerabilityIds": ["CVE-2026-1731"], "sourcePage": 8},
    {"id": "evt-2026-03-scan", "date": "2026-03", "targetCategory": "US Senate and hospital system", "activity": "vulnerability scanning", "outcome": "unsuccessful access attempts", "sourcePage": 8},
    {"id": "evt-2026-06-election", "date": "2026-06", "targetCategory": "US election system", "activity": "QScan vulnerability scanning", "outcome": "unsuccessful access attempt", "toolIds": ["qscan"], "sourcePage": 8},
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
        "The advisory describes QScan, QTRouter, and multiple botnet management platforms as parts of the QTFY ecosystem.",
        "The advisory maps QTFY behavior to MITRE ATT&CK techniques T1595.002, T1190, T1505.003, T1583.003, and T1587.",
        "The advisory's key defensive actions are patching, protecting operational information, isolating critical systems from edge devices, and hunting IOCs.",
        "The advisory recommends investigating and vetting indicators before consequential defensive action.",
        "The advisory recommends continuously exercising, testing, and tuning security controls against the mapped ATT&CK techniques.",
        "The repository source pack preserves organizations, tools, vulnerabilities, and campaign events with source-page provenance.",
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
    """Treat an IOC match as a defensive lead rather than automatic block authority."""
    if not indicator_match:
        return {"matched": False, "action": "none", "humanReviewRequired": False}
    return {
        "matched": True,
        "action": "investigate-and-vet",
        "corroborated": bool(corroborated),
        "autoBlock": False,
        "humanReviewRequired": True,
        "reason": "JCSA-20260826-01 indicators are defensive evidence and require context before consequential action.",
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
        organizations=ORGANIZATIONS,
        tools=THREAT_TOOLS,
        vulnerabilities=VULNERABILITIES,
        campaign_events=CAMPAIGN_EVENTS,
    )
    return {
        "advisoryId": ADVISORY_ID,
        "source": ADVISORY_URL,
        "sourcePack": SOURCE_PACK_PATH,
        "tlp": TLP,
        "published": PUBLISHED,
        "threat": THREAT_LABEL,
        "mission": "DEFEND_AUTHORIZED_ENVIRONMENTS_AGAINST_QTFY_TTPS",
        "mode": "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "targetSectors": list(TARGET_SECTORS),
        "organizations": list(ORGANIZATIONS),
        "tools": list(THREAT_TOOLS),
        "vulnerabilities": list(VULNERABILITIES),
        "campaignEvents": list(CAMPAIGN_EVENTS),
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
            "qtfy-source-pack-loaded",
            "qtfy-hunt-complete",
            "exposed-edge-risk-reviewed",
            "critical-segmentation-verified",
            "compromise-contained-if-present",
            "recovery-validated-if-required",
            "attack-control-tests-recorded",
            "evidence-recorded",
        ],
    }
