from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass(slots=True)
class Judgment:
    verdict: str
    priority: int
    confidence: float
    reasons: list[str] = field(default_factory=list)
    ontology: dict[str, list[str]] = field(default_factory=dict)
    recommended_mode: str = "d"
    provenance: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OntologyJudge:
    """Provenance-first defensive judgment; O-mode means authorized lab simulation only."""

    def judge(self, *, cve: str | None = None, kev_record: dict | None = None, ssvc: dict | None = None, attack_techniques: list[str] | None = None, oscal_controls: list[str] | None = None, osint_evidence: list[dict] | None = None) -> Judgment:
        score = 0
        reasons: list[str] = []
        provenance: list[str] = []
        ontology = {"vulnerability": [], "behavior": [], "controls": [], "osint": []}

        if cve:
            ontology["vulnerability"].append(cve)
        if kev_record:
            score += 4
            provenance.append("CISA KEV")
            reasons.append("CISA marks the vulnerability as known exploited.")
            if kev_record.get("knownRansomwareCampaignUse") == "Known":
                score += 2
                reasons.append("CISA associates it with known ransomware campaign use.")
        if ssvc:
            provenance.append("CISA Vulnrichment/SSVC")
            if str(ssvc.get("Exploitation", "")).lower() == "active":
                score += 3
                reasons.append("SSVC exploitation state is active.")
            if str(ssvc.get("Automatable", "")).lower() == "yes":
                score += 1
                reasons.append("SSVC indicates exploitation is automatable.")
            if str(ssvc.get("Technical Impact", "")).lower() == "total":
                score += 2
                reasons.append("SSVC technical impact is total.")

        techniques = attack_techniques or []
        if techniques:
            provenance.append("MITRE ATT&CK / CISA Decider mapping")
            ontology["behavior"].extend(sorted(set(techniques)))
            score += min(2, len(set(techniques)))
            reasons.append(f"{len(set(techniques))} ATT&CK technique mapping(s) supplied.")

        controls = oscal_controls or []
        if controls:
            provenance.append("NIST OSCAL / SP 800-53")
            ontology["controls"].extend(sorted(set(controls)))
            reasons.append(f"{len(set(controls))} NIST control mapping(s) supplied.")

        evidence = osint_evidence or []
        if evidence:
            provenance.append("OSINT evidence")
            providers = sorted({str(item.get("provider", "unknown")) for item in evidence if isinstance(item, dict)})
            ontology["osint"].extend(providers)
            score += 1
            reasons.append("OSINT evidence is present; treat it as untrusted until corroborated.")

        score = min(score, 10)
        if score >= 8:
            verdict, mode = "CONTAIN_OR_PATCH_NOW", "od"
        elif score >= 5:
            verdict, mode = "PRIORITY_INVESTIGATION", "od"
        elif score >= 2:
            verdict, mode = "INVESTIGATE", "d"
        else:
            verdict, mode = "MONITOR", "d"

        signal_groups = sum(bool(x) for x in (kev_record, ssvc, techniques, controls, evidence))
        confidence = round(min(0.95, 0.35 + signal_groups * 0.12), 2)
        if mode == "od":
            reasons.append("O-mode means authorized lab/digital-twin simulation only; D-mode remains defensive.")

        return Judgment(verdict=verdict, priority=score, confidence=confidence, reasons=reasons, ontology=ontology, recommended_mode=mode, provenance=provenance)
