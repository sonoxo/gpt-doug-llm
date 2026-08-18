"""Public-sector compliance guardrails for GPT Doug.

Technical policy mappings only. This module does not grant an ATO, security
clearance, agency approval, CJIS certification, or authorization to process
classified information or Criminal Justice Information (CJI).

Public baselines represented here:
- NIST SP 800-37 Rev. 2 Risk Management Framework (RMF)
- NIST SP 800-53 Rev. 5, Release 5.2.0 controls
- ODNI ICD 503, IC IT Systems Security Risk Management
- ODNI ICD 703/704/705 concepts for classified/SCI protection, personnel
  eligibility, and accredited facilities
- FBI CJIS Security Policy v5.9.5
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from security_text import normalize_security_text


CLASSIFICATION_LEVELS = {
    "UNCLASSIFIED": 0,
    "CUI": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
    "TOP_SECRET": 4,
    "TS_SCI": 5,
}

PROFILE_CONTROLS = {
    "federal": (
        "AC", "AU", "CA", "CM", "CP", "IA", "IR", "MA", "MP", "PE",
        "PL", "PM", "PS", "PT", "RA", "SA", "SC", "SI", "SR",
    ),
    "ic": (
        "NIST-RMF", "NIST-800-53", "ICD-503", "ICD-703", "ICD-704",
        "ICD-705", "NEED-TO-KNOW", "AUDIT", "HUMAN-OVERSIGHT",
    ),
    "cjis": (
        "CJIS-5.9.5", "ACCESS-CONTROL", "MFA", "AUDIT", "ENCRYPTION",
        "MEDIA-PROTECTION", "INCIDENT-RESPONSE", "PERSONNEL-SECURITY",
    ),
}


@dataclass(frozen=True)
class UserContext:
    jurisdiction: str
    organization_type: str
    role: str
    age_verified: bool
    government_authorized: bool
    human_oversight: bool
    compliance_profile: str = "commercial"
    system_authorized: bool = False
    approved_system_boundary: bool = False
    personnel_eligible: bool = False
    need_to_know: bool = False
    sci_access_authorized: bool = False
    approved_classified_facility: bool = False
    cji_authorized: bool = False
    mfa_enforced: bool = False
    encryption_enforced: bool = False
    audit_enforced: bool = False
    incident_response_ready: bool = False
    classification_ceiling: str = "UNCLASSIFIED"

    @classmethod
    def from_environment(cls) -> "UserContext":
        ceiling = os.getenv("GPT_DOUG_CLASSIFICATION_CEILING", "UNCLASSIFIED").upper()
        if ceiling not in CLASSIFICATION_LEVELS:
            ceiling = "UNCLASSIFIED"
        return cls(
            jurisdiction=os.getenv("GPT_DOUG_JURISDICTION", "UNSPECIFIED").upper(),
            organization_type=os.getenv("GPT_DOUG_ORG_TYPE", "individual").lower(),
            role=os.getenv("GPT_DOUG_ROLE", "user").lower(),
            age_verified=os.getenv("GPT_DOUG_AGE_VERIFIED", "false").lower() == "true",
            government_authorized=os.getenv("GPT_DOUG_GOV_AUTHORIZED", "false").lower() == "true",
            human_oversight=os.getenv("GPT_DOUG_HUMAN_OVERSIGHT", "true").lower() == "true",
            compliance_profile=os.getenv("GPT_DOUG_COMPLIANCE_PROFILE", "commercial").lower(),
            system_authorized=os.getenv("GPT_DOUG_SYSTEM_AUTHORIZED", "false").lower() == "true",
            approved_system_boundary=os.getenv("GPT_DOUG_APPROVED_SYSTEM_BOUNDARY", "false").lower() == "true",
            personnel_eligible=os.getenv("GPT_DOUG_PERSONNEL_ELIGIBLE", "false").lower() == "true",
            need_to_know=os.getenv("GPT_DOUG_NEED_TO_KNOW", "false").lower() == "true",
            sci_access_authorized=os.getenv("GPT_DOUG_SCI_ACCESS_AUTHORIZED", "false").lower() == "true",
            approved_classified_facility=os.getenv("GPT_DOUG_APPROVED_CLASSIFIED_FACILITY", "false").lower() == "true",
            cji_authorized=os.getenv("GPT_DOUG_CJI_AUTHORIZED", "false").lower() == "true",
            mfa_enforced=os.getenv("GPT_DOUG_MFA_ENFORCED", "false").lower() == "true",
            encryption_enforced=os.getenv("GPT_DOUG_ENCRYPTION_ENFORCED", "false").lower() == "true",
            audit_enforced=os.getenv("GPT_DOUG_AUDIT_ENFORCED", "false").lower() == "true",
            incident_response_ready=os.getenv("GPT_DOUG_IR_READY", "false").lower() == "true",
            classification_ceiling=ceiling,
        )


@dataclass(frozen=True)
class ComplianceDecision:
    allowed: bool
    reason: str = ""
    requires_review: bool = False
    control_ids: tuple[str, ...] = ()


class ComplianceGate:
    """Fail-closed policy gate for commercial and public-sector profiles."""

    PROHIBITED = (
        (re.compile(r"(?i)\b(?:autonom\w*|automat\w*)\b.{0,50}\b(?:weapon|target\w*|lethal|combat|drone)\b"), "autonomous weapons or targeting"),
        (re.compile(r"(?i)\b(?:weapon|drone)\b.{0,50}\b(?:target selection|targeting)\b"), "autonomous weapons or targeting"),
        (re.compile(r"(?i)\b(?:social scoring|citizen score)\b"), "social scoring"),
        (re.compile(r"(?i)\b(?:infer|classify|rank)\b.{0,40}\b(?:race|religion|sexual orientation|disability|ethnicity)\b"), "protected-trait inference"),
        (re.compile(r"(?i)\b(?:deepfake|impersonate)\b.{0,30}\b(?:official|election|candidate)\b"), "deceptive civic impersonation"),
    )
    HIGH_IMPACT = re.compile(r"(?i)\b(?:employment|hiring|credit|loan|housing|benefits|healthcare|education admission|law enforcement)\b")
    GOVERNMENT = re.compile(r"(?i)\b(?:government|defen[cs]e|military|intelligence agency|classified|cjis|criminal justice)\b")
    CJI = re.compile(r"(?i)\b(?:criminal justice information|\bcji\b|cjis)\b")
    TS = re.compile(r"(?i)\b(?:top secret|ts//|ts/sci|ts\\sci|sensitive compartmented information|\bsci\b)\b")
    SECRET = re.compile(r"(?i)\b(?:secret//|classified secret|\bsecret material\b)\b")
    CONFIDENTIAL = re.compile(r"(?i)\b(?:confidential//|classified confidential)\b")
    CUI = re.compile(r"(?i)\b(?:cui//|controlled unclassified information|\bcui\b)\b")

    def __init__(self, context: UserContext):
        self.context = context

    def _declared_level(self, text: str) -> str:
        if self.TS.search(text):
            return "TS_SCI" if re.search(r"(?i)(?:ts/sci|sensitive compartmented information|\bsci\b)", text) else "TOP_SECRET"
        if self.SECRET.search(text):
            return "SECRET"
        if self.CONFIDENTIAL.search(text):
            return "CONFIDENTIAL"
        if self.CUI.search(text):
            return "CUI"
        return "UNCLASSIFIED"

    def _government_ready(self) -> bool:
        c = self.context
        return (
            c.organization_type == "government"
            and c.government_authorized
            and c.human_oversight
            and c.system_authorized
            and c.approved_system_boundary
            and c.audit_enforced
        )

    def _classified_ready(self, level: str) -> tuple[bool, str]:
        c = self.context
        if not self._government_ready():
            return False, "classified handling requires an authorized government system boundary with continuous audit and human oversight"
        if not c.personnel_eligible or not c.need_to_know:
            return False, "classified handling requires verified personnel eligibility and need-to-know"
        if not c.approved_classified_facility:
            return False, "classified handling requires an approved classified processing facility/environment"
        if CLASSIFICATION_LEVELS[level] > CLASSIFICATION_LEVELS.get(c.classification_ceiling, 0):
            return False, f"requested classification {level} exceeds configured system ceiling {c.classification_ceiling}"
        if level == "TS_SCI" and not c.sci_access_authorized:
            return False, "SCI handling requires explicit compartment/access authorization"
        return True, ""

    def _cjis_ready(self) -> tuple[bool, str]:
        c = self.context
        if not self._government_ready() or not c.cji_authorized:
            return False, "CJI handling requires an authorized CJIS/CJI environment and system boundary"
        if not (c.mfa_enforced and c.encryption_enforced and c.audit_enforced and c.incident_response_ready):
            return False, "CJI handling requires MFA, encryption, audit logging, and incident-response readiness"
        return True, ""

    def inspect(self, text: str) -> ComplianceDecision:
        text = normalize_security_text(text)
        for pattern, label in self.PROHIBITED:
            if pattern.search(text):
                return ComplianceDecision(False, f"prohibited use: {label}", control_ids=("PROHIBITED-USE",))

        level = self._declared_level(text)
        if level != "UNCLASSIFIED":
            ready, reason = self._classified_ready(level)
            if not ready:
                return ComplianceDecision(False, reason, control_ids=("ICD-503", "ICD-703", "ICD-704", "ICD-705"))
            return ComplianceDecision(True, "classified handling requires recorded security review", True, ("ICD-503", "ICD-703", "ICD-704", "ICD-705", "AU"))

        if self.CJI.search(text):
            ready, reason = self._cjis_ready()
            if not ready:
                return ComplianceDecision(False, reason, control_ids=("CJIS-5.9.5", "IA", "SC", "AU", "IR"))
            return ComplianceDecision(True, "CJI handling requires recorded human review", True, ("CJIS-5.9.5", "IA", "SC", "AU", "IR"))

        if self.GOVERNMENT.search(text) or self.context.compliance_profile in {"federal", "ic", "cjis"}:
            if not self._government_ready():
                return ComplianceDecision(False, "government profile requires verified organization authorization, authorized system boundary, audit enforcement, and human oversight", control_ids=("NIST-RMF", "CA", "AU"))
            return ComplianceDecision(True, "government use requires recorded human review", True, ("NIST-RMF", "NIST-800-53", "CA", "AU"))

        if self.HIGH_IMPACT.search(text):
            if not self.context.human_oversight:
                return ComplianceDecision(False, "high-impact use requires human oversight", control_ids=("HUMAN-OVERSIGHT",))
            return ComplianceDecision(True, "high-impact decision support requires human review", True, ("HUMAN-OVERSIGHT",))

        return ComplianceDecision(True)

    def status(self) -> str:
        c = self.context
        profile = c.compliance_profile
        controls = ",".join(PROFILE_CONTROLS.get(profile, ())) or "baseline"
        return (
            f"jurisdiction={c.jurisdiction} // org={c.organization_type} // role={c.role} "
            f"// profile={profile} // ceiling={c.classification_ceiling} "
            f"// gov_auth={c.government_authorized} // system_auth={c.system_authorized} "
            f"// human_oversight={c.human_oversight} // controls={controls}"
        )
