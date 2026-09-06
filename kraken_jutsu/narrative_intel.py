from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable


class ClaimStatus(str, Enum):
    CLAIMED = "CLAIMED"
    CORROBORATED = "CORROBORATED"
    VERIFIED_INCIDENT = "VERIFIED_INCIDENT"
    DISPUTED = "DISPUTED"
    RETRACTED = "RETRACTED"


class EvidenceKind(str, Enum):
    ACTOR_CLAIM = "actor_claim"
    SOCIAL_POST = "social_post"
    NEWS_REPORT = "news_report"
    THIRD_PARTY_REPORT = "third_party_report"
    GOVERNMENT_ADVISORY = "government_advisory"
    VICTIM_STATEMENT = "victim_statement"
    TELEMETRY = "telemetry"
    IOC_MATCH = "ioc_match"


DEFAULT_EVIDENCE_WEIGHTS: dict[EvidenceKind, float] = {
    EvidenceKind.ACTOR_CLAIM: 0.10,
    EvidenceKind.SOCIAL_POST: 0.08,
    EvidenceKind.NEWS_REPORT: 0.20,
    EvidenceKind.THIRD_PARTY_REPORT: 0.24,
    EvidenceKind.GOVERNMENT_ADVISORY: 0.32,
    EvidenceKind.VICTIM_STATEMENT: 0.38,
    EvidenceKind.TELEMETRY: 0.45,
    EvidenceKind.IOC_MATCH: 0.30,
}

AUTHORITATIVE_KINDS = {
    EvidenceKind.GOVERNMENT_ADVISORY,
    EvidenceKind.VICTIM_STATEMENT,
    EvidenceKind.TELEMETRY,
}

TECHNICAL_KINDS = {
    EvidenceKind.TELEMETRY,
    EvidenceKind.IOC_MATCH,
}


@dataclass(frozen=True, slots=True)
class Evidence:
    source_id: str
    kind: EvidenceKind
    reliability: float = 0.5
    independent: bool = True
    supports: bool = True
    provider: str = ""
    reference: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between 0 and 1")


@dataclass(slots=True)
class ThreatClaim:
    claim_id: str
    event: str
    narrative: str
    actor: str = "unknown"
    motivations: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    ttps: list[str] = field(default_factory=list)
    observables: list[str] = field(default_factory=list)
    impacts: list[str] = field(default_factory=list)
    defenses: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    retracted: bool = False

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id is required")
        if not self.event.strip():
            raise ValueError("event is required")
        if not self.narrative.strip():
            raise ValueError("narrative is required")


@dataclass(slots=True)
class VerificationResult:
    claim_id: str
    status: ClaimStatus
    confidence: float
    reasons: list[str]
    provenance: list[str]
    independent_sources: int
    authoritative_sources: int
    technical_sources: int
    ontology: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class ClaimVerifier:
    """Deterministic, explainable verifier for defensive cyber-intelligence claims.

    Invariant: a public claim is never treated as a compromise merely because an
    actor, social account, or single report says it happened.
    """

    def __init__(
        self,
        *,
        corroborated_threshold: float = 0.40,
        verified_threshold: float = 0.70,
        weights: dict[EvidenceKind, float] | None = None,
    ) -> None:
        if not 0.0 <= corroborated_threshold < verified_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= corroborated < verified <= 1")
        self.corroborated_threshold = corroborated_threshold
        self.verified_threshold = verified_threshold
        self.weights = dict(DEFAULT_EVIDENCE_WEIGHTS if weights is None else weights)

    @staticmethod
    def _dedupe_evidence(evidence: Iterable[Evidence]) -> list[Evidence]:
        best: dict[tuple[str, EvidenceKind, bool], Evidence] = {}
        for item in evidence:
            key = (item.source_id.strip().lower(), item.kind, item.supports)
            current = best.get(key)
            if current is None or item.reliability > current.reliability:
                best[key] = item
        return list(best.values())

    def verify(self, claim: ThreatClaim) -> VerificationResult:
        if claim.retracted:
            return VerificationResult(
                claim_id=claim.claim_id,
                status=ClaimStatus.RETRACTED,
                confidence=0.0,
                reasons=["The claim is explicitly marked retracted."],
                provenance=[],
                independent_sources=0,
                authoritative_sources=0,
                technical_sources=0,
                ontology=self._ontology(claim, ClaimStatus.RETRACTED, 0.0),
            )

        evidence = self._dedupe_evidence(claim.evidence)
        supporting = [e for e in evidence if e.supports]
        contradicting = [e for e in evidence if not e.supports]

        supporting_score = sum(
            self.weights.get(e.kind, 0.10) * e.reliability for e in supporting
        )
        contradicting_score = sum(
            self.weights.get(e.kind, 0.10) * e.reliability for e in contradicting
        )

        # Multiple independent sources matter, but cap their bonus to keep a
        # pile of weak social posts from manufacturing "verification".
        independent_ids = {
            e.source_id.strip().lower()
            for e in supporting
            if e.independent and e.kind is not EvidenceKind.ACTOR_CLAIM
        }
        independent_bonus = min(0.16, max(0, len(independent_ids) - 1) * 0.08)

        raw = supporting_score + independent_bonus - contradicting_score
        confidence = round(max(0.0, min(0.99, raw)), 2)

        authoritative = [
            e for e in supporting if e.kind in AUTHORITATIVE_KINDS and e.reliability >= 0.60
        ]
        technical = [
            e for e in supporting if e.kind in TECHNICAL_KINDS and e.reliability >= 0.60
        ]
        strong_contradiction = any(
            e.kind in AUTHORITATIVE_KINDS and e.reliability >= 0.70
            for e in contradicting
        )

        reasons: list[str] = []
        if not supporting:
            reasons.append("No supporting evidence was supplied.")
        if any(e.kind is EvidenceKind.ACTOR_CLAIM for e in supporting):
            reasons.append("Actor self-claims are treated as claims, not proof of compromise.")
        if independent_ids:
            reasons.append(f"{len(independent_ids)} independent supporting source(s) were supplied.")
        if authoritative:
            reasons.append(f"{len(authoritative)} authoritative evidence source(s) support the claim.")
        if technical:
            reasons.append(f"{len(technical)} technical evidence source(s) support the claim.")
        if contradicting:
            reasons.append(f"{len(contradicting)} source(s) contradict the claim.")

        if strong_contradiction and contradicting_score >= supporting_score:
            status = ClaimStatus.DISPUTED
            reasons.append("Strong authoritative contradiction prevents incident verification.")
        elif (
            confidence >= self.verified_threshold
            and len(independent_ids) >= 2
            and authoritative
            and technical
        ):
            status = ClaimStatus.VERIFIED_INCIDENT
            reasons.append(
                "Verification threshold met with independent, authoritative, and technical corroboration."
            )
        elif confidence >= self.corroborated_threshold and len(independent_ids) >= 2:
            status = ClaimStatus.CORROBORATED
            reasons.append("Multiple independent sources corroborate the claim.")
        else:
            status = ClaimStatus.CLAIMED
            reasons.append("Evidence does not meet the corroboration requirements.")

        provenance = sorted(
            {
                f"{e.provider or e.source_id}:{e.kind.value}"
                for e in evidence
            }
        )
        return VerificationResult(
            claim_id=claim.claim_id,
            status=status,
            confidence=confidence,
            reasons=reasons,
            provenance=provenance,
            independent_sources=len(independent_ids),
            authoritative_sources=len(authoritative),
            technical_sources=len(technical),
            ontology=self._ontology(claim, status, confidence),
        )

    @staticmethod
    def _ontology(
        claim: ThreatClaim,
        status: ClaimStatus,
        confidence: float,
    ) -> dict[str, Any]:
        # Stable order mirrors the Actor–Narrative–Cyber reasoning chain:
        # EVENT → NARRATIVE → ACTOR → MOTIVATION → TARGET → TTP →
        # OBSERVABLE → IMPACT → DEFENSE → CONFIDENCE.
        return {
            "event": claim.event,
            "narrative": claim.narrative,
            "actor": claim.actor,
            "motivation": sorted(set(claim.motivations)),
            "target": sorted(set(claim.targets)),
            "ttp": sorted(set(claim.ttps)),
            "observable": sorted(set(claim.observables)),
            "impact": sorted(set(claim.impacts)),
            "defense": sorted(set(claim.defenses)),
            "confidence": confidence,
            "claim_status": status.value,
        }


def build_defensive_brief(
    claim: ThreatClaim,
    result: VerificationResult,
) -> dict[str, Any]:
    """Build a non-operational defensive brief suitable for SOC/IR workflows."""
    posture = {
        ClaimStatus.CLAIMED: "MONITOR_AND_CORROBORATE",
        ClaimStatus.CORROBORATED: "PRIORITY_INVESTIGATION",
        ClaimStatus.VERIFIED_INCIDENT: "DEFENSIVE_RESPONSE",
        ClaimStatus.DISPUTED: "HOLD_ATTRIBUTION",
        ClaimStatus.RETRACTED: "CLOSE_OR_ARCHIVE",
    }[result.status]
    return {
        "claim_id": claim.claim_id,
        "posture": posture,
        "status": result.status.value,
        "confidence": result.confidence,
        "ontology": result.ontology,
        "recommended_actions": [
            "Preserve provenance and timestamps for every evidence item.",
            "Correlate claims with owned or authorized telemetry.",
            "Map observed behavior to defensive ATT&CK detections and controls.",
            "Escalate containment only when affected infrastructure or trusted telemetry supports it.",
            "Keep attribution hypotheses separate from incident verification.",
        ],
        "reasons": result.reasons,
        "provenance": result.provenance,
    }
