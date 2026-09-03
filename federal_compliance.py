"""Public-sector security alignment gate for GPT-DOUG / Virginia-LLM.

This module records controls and evidence targets derived from public U.S.
government guidance. It does not claim an ATO, agency certification, CIA
approval, or authorization to process classified information.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


PUBLIC_AUTHORITIES = [
    {
        "agency": "DoD / U.S. Space Force",
        "title": "DoD AI Cybersecurity Risk Management Tailoring Guide",
        "url": "https://dodcio.defense.gov/Portals/0/Documents/Library/AI-CybersecurityRMTailoringGuide.pdf",
        "purpose": "DoDI 8510.01 RMF-aligned cybersecurity tailoring for AI systems.",
    },
    {
        "agency": "U.S. Space Force",
        "title": "U.S. Space Force Commercial Space Strategy",
        "url": "https://www.spaceforce.mil/Portals/2/Documents/Space%20Policy/USSF_Commercial_Space_Strategy.pdf",
        "purpose": "Cybersecurity, mission assurance, NSA/NIST/DISA standards and Zero Trust expectations for commercial integration.",
    },
    {
        "agency": "NSA",
        "title": "NSA Zero Trust Guidance",
        "url": "https://www.nsa.gov/Cybersecurity/ZIG/CSIs/",
        "purpose": "Zero Trust maturity guidance for NSS and other network owners/operators.",
    },
    {
        "agency": "NSA",
        "title": "Post-Quantum Cybersecurity Resources / CNSA 2.0",
        "url": "https://www.nsa.gov/Cybersecurity/Post-Quantum-Cybersecurity-Resources/",
        "purpose": "Public CNSA 2.0 and CNSS Policy 15 transition guidance for NSS cryptography.",
    },
    {
        "agency": "NASA",
        "title": "NPR 2810.1F — Security of Information and Information Systems",
        "url": "https://nodis3.gsfc.nasa.gov/displayDir.cfm?Internal_ID=N_PR_2810_001F_&page_name=Preface",
        "purpose": "NASA information-security requirements aligned to NIST SP 800-37 and SP 800-53.",
    },
    {
        "agency": "ODNI / Intelligence Community",
        "title": "Intelligence Community Directives index — ICD 502, 503, 703, 731 and related directives",
        "url": "https://www.dni.gov/index.php/who-we-are/organizations/policy-capabilities/ps/ps-related-menus/ps-related-links/policy-division/intelligence-community-directives",
        "purpose": "Public IC policy baseline relevant to CIA/IC information-system risk management and protection.",
    },
    {
        "agency": "NIST",
        "title": "NIST SP 800-53 Rev. 5, Release 5.2.0",
        "url": "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
        "purpose": "Federal security and privacy control catalog used as the common control vocabulary.",
    },
]


@dataclass(frozen=True)
class AgencyAlignment:
    name: str
    scope: str
    status: str
    public_basis: tuple[str, ...]
    evidence_required: tuple[str, ...]
    limitation: str


class FederalComplianceProfile:
    """Evaluate whether the local configuration is ready for formal assessment."""

    def __init__(self, foundry: Optional[Any] = None) -> None:
        self.foundry = foundry

    def controls(self) -> dict[str, bool]:
        foundry_pinned = self.foundry is None or bool(getattr(self.foundry, "allowed_host", ""))
        redirect_safe = self.foundry is None or getattr(self.foundry, "redirect_policy", "") == "same-host-https-only"
        writes_disabled_or_gated = self.foundry is None or (
            not bool(getattr(self.foundry, "writes_enabled", False))
            or _flag("GOV_HUMAN_APPROVAL_REQUIRED", True)
        )
        classified_requested = _flag("GOV_ALLOW_CLASSIFIED", False)
        classified_env_authorized = _flag("GOV_CLASSIFIED_ENVIRONMENT_AUTHORIZED", False)

        return {
            "AC_least_privilege": _flag("GOV_LEAST_PRIVILEGE", True),
            "AU_audit_required": _flag("GOV_AUDIT_REQUIRED", True),
            "CA_continuous_assessment": _flag("GOV_CONTINUOUS_ASSESSMENT", True),
            "CM_change_control": _flag("GOV_CHANGE_CONTROL", True),
            "IA_identity_verification": _flag("GOV_IDENTITY_VERIFICATION", True),
            "SC_tls_and_host_pinning": foundry_pinned,
            "SC_redirect_boundary": redirect_safe,
            "SI_fail_closed": _flag("GOV_FAIL_CLOSED", True),
            "SR_supply_chain_evidence": _flag("GOV_SUPPLY_CHAIN_EVIDENCE", True),
            "ZT_zero_trust": _flag("GOV_ZERO_TRUST", True),
            "HITL_consequential_writes": writes_disabled_or_gated,
            "DATA_no_unapproved_classified_processing": (not classified_requested) or classified_env_authorized,
            "EGRESS_remote_model_egress_disabled": not _flag("GOV_ALLOW_REMOTE_MODEL_EGRESS", False),
        }

    def _agency_alignments(self, ready: bool) -> list[AgencyAlignment]:
        status = "assessment-ready" if ready else "control-gap"
        common_evidence = (
            "system security plan / architecture boundary",
            "identity and access-control evidence",
            "audit logging and retention evidence",
            "configuration/change-management evidence",
            "incident-response and recovery evidence",
            "supply-chain/dependency evidence",
            "control assessment results and remediation tracking",
        )
        return [
            AgencyAlignment(
                "U.S. Space Force / DoD",
                "DoD RMF and cyber-resilient/Zero-Trust software architecture",
                status,
                ("DoDI 8510.01", "DoD AI Cybersecurity RM Tailoring Guide", "USSF Commercial Space Strategy"),
                common_evidence + ("Authorizing Official decision / ATO where required",),
                "Repository alignment is not a DoD or Space Force ATO.",
            ),
            AgencyAlignment(
                "NSA / National Security Systems",
                "Public NSA Zero Trust, CNSA 2.0 transition and NSS hardening expectations",
                status,
                ("NSA Zero Trust CSIs", "CNSA 2.0", "CNSS Policy 15 / CNSSI-1253 mappings where applicable"),
                common_evidence + ("approved cryptographic implementation evidence for the target NSS environment",),
                "Actual NSS/classified use requires the applicable CNSS/NSA-approved environment, products and authorization.",
            ),
            AgencyAlignment(
                "NASA",
                "NASA information-system security lifecycle aligned to NIST RMF",
                status,
                ("NPR 2810.1F", "NIST SP 800-37", "NIST SP 800-53"),
                common_evidence + ("NASA system-owner and authorization artifacts when deployed for NASA",),
                "Repository alignment is not NASA authorization or acceptance.",
            ),
            AgencyAlignment(
                "CIA / Intelligence Community",
                "Public IC information-system risk management and protection directives",
                status,
                ("ICD 502", "ICD 503", "ICD 703", "ICD 731"),
                common_evidence + ("IC-element-specific controls, markings, accreditation and authorization evidence",),
                "CIA-specific internal requirements are not fully public; this project cannot claim CIA certification or approval.",
            ),
        ]

    def status(self) -> dict[str, Any]:
        controls = self.controls()
        ready = all(controls.values())
        data_mode = os.getenv("GOV_DATA_MODE", "PUBLIC-UNCLASSIFIED").strip().upper() or "PUBLIC-UNCLASSIFIED"
        return {
            "profile": "us-federal-ic-public-alignment-v1",
            "assessment_state": "assessment-ready" if ready else "control-gap",
            "certification": {
                "certified": False,
                "ato": False,
                "cia_approved": False,
                "statement": "Control alignment only. Formal authorization/certification must be issued by the responsible agency/Authorizing Official.",
            },
            "data_mode": data_mode,
            "controls": controls,
            "agency_alignment": [asdict(item) for item in self._agency_alignments(ready)],
            "public_authorities": PUBLIC_AUTHORITIES,
            "release_gate": [
                "all required controls true",
                "no classified processing unless explicitly authorized in the target environment",
                "no remote model egress unless separately approved for the data classification",
                "human approval for consequential writes",
                "preserve markings, provenance, audit records and least privilege",
                "complete agency-specific assessment/authorization before production government use",
            ],
        }
