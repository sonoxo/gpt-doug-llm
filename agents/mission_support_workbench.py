"""Analyst-facing mission support workbench for ZYRA / XUNIA.

The module performs evidence normalization, case correlation, confidence/quality
aggregation, review prioritization, and Maven/Foundry-friendly event generation.
It is read-only decision support and has no external actuation path.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

MODE = "ANALYST_DECISION_SUPPORT"
ALLOWED_SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH"}

FORBIDDEN_FIELDS = {
    "person_id",
    "person_name",
    "biometric",
    "face_id",
    "phone_number",
    "external_action",
    "actuation_command",
}


def _scan_forbidden(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_FIELDS:
                raise ValueError(f"restricted field is not permitted: {path}.{key}")
            _scan_forbidden(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _scan_forbidden(nested, f"{path}[{index}]")


def _unit_interval(value: Any, field: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return number


def _utc_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("observedAt must be an ISO-8601 timestamp")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_evidence(item: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one authorized, non-identifying evidence record."""

    if not isinstance(item, Mapping):
        raise TypeError("evidence item must be a mapping")
    _scan_forbidden(item)

    evidence_id = str(item.get("evidenceId", "")).strip()
    case_id = str(item.get("caseId", "")).strip()
    source = str(item.get("source", "")).strip()
    category = str(item.get("category", "general")).strip() or "general"
    severity = str(item.get("severity", "INFO")).upper()

    if not evidence_id:
        raise ValueError("evidenceId is required")
    if not case_id:
        raise ValueError("caseId is required")
    if not source:
        raise ValueError("source is required")
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"severity must be one of {sorted(ALLOWED_SEVERITIES)}")

    normalized = {
        "evidenceId": evidence_id,
        "caseId": case_id,
        "observedAt": _utc_timestamp(item.get("observedAt")),
        "source": source,
        "category": category,
        "severity": severity,
        "confidence": _unit_interval(item.get("confidence", 1.0), "confidence"),
        "quality": _unit_interval(item.get("quality", 1.0), "quality"),
        "summary": str(item.get("summary", "")).strip(),
        "metadata": deepcopy(dict(item.get("metadata", {}))),
    }
    _scan_forbidden(normalized)
    return normalized


def correlate_case(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate one case into an analyst review packet."""

    evidence = [normalize_evidence(item) for item in items]
    if not evidence:
        raise ValueError("at least one evidence item is required")

    case_ids = {item["caseId"] for item in evidence}
    if len(case_ids) != 1:
        raise ValueError("all evidence items in a packet must share caseId")

    evidence.sort(key=lambda item: item["observedAt"])
    sources = sorted({item["source"] for item in evidence})
    confidence = sum(item["confidence"] for item in evidence) / len(evidence)
    quality = sum(item["quality"] for item in evidence) / len(evidence)
    severity_rank = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    severity = max(evidence, key=lambda item: severity_rank[item["severity"]])["severity"]

    review_priority = round(
        min(
            1.0,
            (confidence * 0.35)
            + (quality * 0.30)
            + (min(len(sources), 4) / 4.0 * 0.20)
            + (severity_rank[severity] / 3.0 * 0.15),
        ),
        4,
    )

    return {
        "mode": MODE,
        "packetId": f"review:{evidence[0]['caseId']}:{evidence[-1]['observedAt']}",
        "caseId": evidence[0]["caseId"],
        "firstObservedAt": evidence[0]["observedAt"],
        "lastObservedAt": evidence[-1]["observedAt"],
        "evidenceCount": len(evidence),
        "sourceCount": len(sources),
        "sources": sources,
        "meanConfidence": round(confidence, 4),
        "meanQuality": round(quality, 4),
        "highestSeverity": severity,
        "reviewPriority": review_priority,
        "reviewStatus": "PENDING_HUMAN_REVIEW",
        "recommendedAction": "REVIEW_EVIDENCE",
        "automaticExternalAction": False,
        "evidence": evidence,
    }


def build_maven_event(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Maven/Foundry-friendly ontology event for a review packet."""

    _scan_forbidden(packet)
    if packet.get("mode") != MODE:
        raise ValueError(f"packet mode must be {MODE}")

    return {
        "objectType": "DecisionPacket",
        "objectId": packet["packetId"],
        "properties": {
            "caseId": packet["caseId"],
            "firstObservedAt": packet["firstObservedAt"],
            "lastObservedAt": packet["lastObservedAt"],
            "evidenceCount": packet["evidenceCount"],
            "sourceCount": packet["sourceCount"],
            "meanConfidence": packet["meanConfidence"],
            "meanQuality": packet["meanQuality"],
            "highestSeverity": packet["highestSeverity"],
            "reviewPriority": packet["reviewPriority"],
            "reviewStatus": packet["reviewStatus"],
            "recommendedAction": packet["recommendedAction"],
            "automaticExternalAction": False,
        },
        "links": [
            {
                "relationType": "DERIVED_FROM",
                "objectIds": [item["evidenceId"] for item in packet["evidence"]],
            }
        ],
        "policy": {
            "mode": MODE,
            "humanReviewRequired": True,
            "readOnlyDecisionSupport": True,
            "externalActuation": False,
            "provenanceRequired": True,
        },
    }


def workbench_manifest() -> dict[str, Any]:
    return {
        "name": "ZYRA / XUNIA Mission Support Workbench",
        "mode": MODE,
        "capabilities": [
            "authorized multi-source evidence intake",
            "case correlation",
            "confidence and quality scoring",
            "analyst review prioritization",
            "Maven/Foundry ontology event output",
            "audit-ready provenance",
            "timeline replay compatible state",
        ],
        "controls": {
            "humanReviewRequired": True,
            "externalActuation": False,
            "identityTracking": False,
            "provenanceRequired": True,
        },
    }
