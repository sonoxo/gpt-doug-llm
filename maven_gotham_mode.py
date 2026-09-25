"""GPT-DOUG Maven Gotham Mode: consequence-aware defensive decision support.

"ARTILLERY" in this module means a batched analytic salvo only. This code does
not select weapon targets, compute firing solutions, provide ballistic data,
control weapons, or execute kinetic actions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable


GOTHAM_PROFILE = "XUNIA_MAVEN_GOTHAM_SIMULATION_V1"
ARTILLERY_MODE = "ANALYTIC_SALVO_ONLY"

SEVERITY_WEIGHT = {
    "INFO": 10,
    "LOW": 25,
    "MEDIUM": 50,
    "HIGH": 75,
    "CRITICAL": 90,
}

GOTHAM_INVARIANTS = (
    "DECISION_SUPPORT_AND_SIMULATION_ONLY",
    "NO_WEAPON_TARGET_SELECTION",
    "NO_FIRE_CONTROL_OR_FIRING_SOLUTIONS",
    "NO_KINETIC_STRIKE_EXECUTION",
    "NO_PERSON_LEVEL_TARGET_RANKING",
    "NO_AUTONOMOUS_EXTERNAL_SIDE_EFFECTS",
    "PROVENANCE_AND_CONFIDENCE_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


@dataclass(slots=True, frozen=True)
class ConsequenceEnvelope:
    packet_id: str
    entity_ref: str
    domain: str
    score: int
    confidence: float
    service_continuity: int
    data_integrity: int
    public_safety: int
    recovery_complexity: int
    resource_strain: int
    execution: str = "SIMULATION_ONLY"


@dataclass(slots=True, frozen=True)
class AnalyticRound:
    order: int
    packet_id: str
    entity_ref: str
    domain: str
    consequence_score: int
    confidence: float
    review_state: str


def consequence_envelope(packet: dict) -> ConsequenceEnvelope:
    """Create a defensive operational-impact estimate from a Maven packet."""
    assessment = packet.get("assessment") or {}
    track = packet.get("track") or {}
    severity = str(assessment.get("severity", "INFO")).upper()
    confidence = _clamp(float(assessment.get("confidence", 0.0)), 0.0, 1.0)
    domain = str(packet.get("domain") or track.get("domain") or "TRAINING").upper()
    base = SEVERITY_WEIGHT.get(severity, 10)
    actions = assessment.get("recommendedActions") or assessment.get("recommended_actions") or []
    action_pressure = min(12, len(actions) * 2)

    service = int(round(_clamp(base + (12 if domain == "CRITICAL_INFRASTRUCTURE" else 0))))
    integrity = int(round(_clamp(base + (15 if domain == "CYBER_DEFENSE" else 0))))
    safety = int(round(_clamp(base + (15 if domain == "EMERGENCY_MANAGEMENT" else 0))))
    recovery = int(round(_clamp(base + action_pressure)))
    strain = int(round(_clamp(base + (12 if domain == "LOGISTICS" else 0))))
    raw = (service + integrity + safety + recovery + strain) / 5
    score = int(round(_clamp(raw * (0.7 + confidence * 0.3))))

    return ConsequenceEnvelope(
        packet_id=str(packet.get("packetId") or packet.get("packet_id") or "unknown"),
        entity_ref=str(track.get("entityRef") or track.get("entity_ref") or "unknown"),
        domain=domain,
        score=score,
        confidence=confidence,
        service_continuity=service,
        data_integrity=integrity,
        public_safety=safety,
        recovery_complexity=recovery,
        resource_strain=strain,
    )


def build_analytic_salvo(packets: Iterable[dict], limit: int = 25) -> dict:
    """Batch consequence-ranked packets for human review; no external actuation."""
    packet_list = list(packets)
    envelopes = [consequence_envelope(packet) for packet in packet_list]
    envelope_by_id = {item.packet_id: item for item in envelopes}

    def packet_id(packet: dict) -> str:
        return str(packet.get("packetId") or packet.get("packet_id") or "unknown")

    ordered = sorted(
        packet_list,
        key=lambda packet: (
            envelope_by_id[packet_id(packet)].score,
            envelope_by_id[packet_id(packet)].confidence,
        ),
        reverse=True,
    )[: max(0, min(int(limit), 25))]

    rounds = []
    for index, packet in enumerate(ordered, start=1):
        pid = packet_id(packet)
        track = packet.get("track") or {}
        env = envelope_by_id[pid]
        rounds.append(
            AnalyticRound(
                order=index,
                packet_id=pid,
                entity_ref=str(track.get("entityRef") or track.get("entity_ref") or "unknown"),
                domain=env.domain,
                consequence_score=env.score,
                confidence=env.confidence,
                review_state=str(packet.get("reviewState") or packet.get("review_state") or "DRAFT"),
            )
        )

    return {
        "profile": GOTHAM_PROFILE,
        "mode": ARTILLERY_MODE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analytic_rounds": [asdict(item) for item in rounds],
        "consequence_envelopes": [asdict(item) for item in envelopes],
        "human_review_required": True,
        "external_side_effects_executed": False,
        "invariants": list(GOTHAM_INVARIANTS),
        "truth_boundary": (
            "ARTILLERY is a metaphor for batched analytic review. Gotham Mode performs "
            "consequence simulation and prioritization only; it does not select weapon targets, "
            "compute firing solutions, or execute kinetic actions."
        ),
    }


if __name__ == "__main__":
    demo_packet = {
        "packetId": "demo-1",
        "domain": "CRITICAL_INFRASTRUCTURE",
        "reviewState": "PENDING_REVIEW",
        "track": {"entityRef": "demo-service"},
        "assessment": {
            "severity": "HIGH",
            "confidence": 0.9,
            "recommendedActions": ["REQUEST_INSPECTION"],
        },
    }
    print(build_analytic_salvo([demo_packet]))
