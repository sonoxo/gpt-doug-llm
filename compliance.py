"""Jurisdiction-aware access policy for GPT Doug.

This module provides technical controls and evidence hooks. It is not legal
advice or a certification of compliance in any jurisdiction.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from security_text import normalize_security_text


@dataclass(frozen=True)
class UserContext:
    jurisdiction: str
    organization_type: str
    role: str
    age_verified: bool
    government_authorized: bool
    human_oversight: bool

    @classmethod
    def from_environment(cls) -> "UserContext":
        return cls(
            jurisdiction=os.getenv("GPT_DOUG_JURISDICTION", "UNSPECIFIED").upper(),
            organization_type=os.getenv("GPT_DOUG_ORG_TYPE", "individual").lower(),
            role=os.getenv("GPT_DOUG_ROLE", "user").lower(),
            age_verified=os.getenv("GPT_DOUG_AGE_VERIFIED", "false").lower() == "true",
            government_authorized=os.getenv("GPT_DOUG_GOV_AUTHORIZED", "false").lower() == "true",
            human_oversight=os.getenv("GPT_DOUG_HUMAN_OVERSIGHT", "true").lower() == "true",
        )


@dataclass(frozen=True)
class ComplianceDecision:
    allowed: bool
    reason: str = ""
    requires_review: bool = False


class ComplianceGate:
    """Conservative baseline policy mapped to declared, verified context.

    Protected traits are deliberately absent from UserContext and must never be
    used to grant, restrict, or personalize access.
    """

    PROHIBITED = (
        (re.compile(r"(?i)\b(?:autonom\w*|automat\w*)\b.{0,50}\b(?:weapon|target\w*|lethal|combat|drone)\b"), "autonomous weapons or targeting"),
        (re.compile(r"(?i)\b(?:weapon|drone)\b.{0,50}\b(?:target selection|targeting)\b"), "autonomous weapons or targeting"),
        (re.compile(r"(?i)\b(?:social scoring|citizen score)\b"), "social scoring"),
        (re.compile(r"(?i)\b(?:infer|classify|rank)\b.{0,40}\b(?:race|religion|sexual orientation|disability|ethnicity)\b"), "protected-trait inference"),
        (re.compile(r"(?i)\b(?:deepfake|impersonate)\b.{0,30}\b(?:official|election|candidate)\b"), "deceptive civic impersonation"),
        (re.compile(r"(?i)\b(?:identify|find|locate|select|rank|recommend)\b.{0,80}\b(?:weak|vulnerable|soft|unguarded)\b.{0,50}\b(?:military|army|naval|airbase|outpost|facility|target)\b"), "real-world military weak-point identification"),
        (re.compile(r"(?i)\b(?:first[- ]strike|strike planning|attack plan|sabotage)\b"), "operational attack planning"),
        (re.compile(r"(?i)\b(?:bypass|evade|defeat)\b.{0,50}\b(?:access control|authentication|security control)\b"), "unauthorized access-control bypass"),
    )
    HIGH_IMPACT = re.compile(r"(?i)\b(?:employment|hiring|credit|loan|housing|benefits|healthcare|education admission|law enforcement)\b")
    GOVERNMENT = re.compile(r"(?i)\b(?:government|defen[cs]e|military|intelligence agency|classified)\b")
    INTELLIGENCE_RESEARCH = re.compile(r"(?i)\b(?:osint|open[- ]source intelligence|intelligence analysis|declassified|public records?|source provenance|analytic confidence)\b")

    def __init__(self, context: UserContext):
        self.context = context

    def inspect(self, text: str) -> ComplianceDecision:
        text = normalize_security_text(text)
        for pattern, label in self.PROHIBITED:
            if pattern.search(text):
                return ComplianceDecision(False, f"prohibited use: {label}")
        if self.GOVERNMENT.search(text):
            if self.context.organization_type != "government" or not self.context.government_authorized:
                return ComplianceDecision(False, "government use requires verified organizational authorization")
            if not self.context.human_oversight:
                return ComplianceDecision(False, "government use requires human oversight")
            return ComplianceDecision(True, "government use requires recorded human review", True)
        if self.HIGH_IMPACT.search(text):
            if not self.context.human_oversight:
                return ComplianceDecision(False, "high-impact use requires human oversight")
            return ComplianceDecision(True, "high-impact decision support requires human review", True)
        if self.INTELLIGENCE_RESEARCH.search(text):
            if not self.context.human_oversight:
                return ComplianceDecision(False, "intelligence research requires human oversight")
            return ComplianceDecision(True, "intelligence research requires provenance and human review", True)
        return ComplianceDecision(True)

    def status(self) -> str:
        return (
            f"jurisdiction={self.context.jurisdiction} // org={self.context.organization_type} "
            f"// role={self.context.role} // human_oversight={self.context.human_oversight}"
        )
