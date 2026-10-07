from __future__ import annotations

from typing import Final

ONTOLOGY_VERSION: Final = "gpt-doug.ontology.v1"

PUBLIC_EVENT_CLASSES: Final = {"PUBLIC", "TRAINING", "SIMULATION"}
ALLOWED_EVENT_CLASSES: Final = {
    "PUBLIC",
    "TRAINING",
    "SIMULATION",
    "BUSINESS_CONFIDENTIAL",
    "FCI",
    "CUI",
}
BLOCKED_OPERATIONAL_EVENT_TYPES: Final = {
    "WEAPON_CONTROL",
    "TARGET_SELECTION",
    "STRIKE_PLANNING",
    "PAYLOAD_RELEASE",
    "LETHAL_ENGAGEMENT",
    "REAL_PERSON_HOSTILE_CLASSIFICATION",
}

ONTOLOGY_SCHEMA: Final = {
    "version": ONTOLOGY_VERSION,
    "entities": {
        "entity": ["id", "kind", "label", "status", "confidence", "sourceId", "provenance"],
        "sensor": ["id", "kind", "label", "status", "freshness", "sourceId", "provenance"],
        "observation": ["id", "entityId", "sensorId", "eventTime", "confidence", "payload"],
        "asset": ["id", "kind", "label", "status", "dependencies"],
        "event": ["id", "eventType", "entityKind", "objectId", "classification", "payload"],
        "dependency": ["id", "sourceId", "targetId", "relation", "confidence"],
        "case": ["id", "caseNumber", "status", "priority"],
        "evidence": ["id", "sourceId", "provenance", "digest", "classification"],
        "decision": ["id", "actor", "decision", "humanApproved", "evidenceRefs"],
        "outcome": ["id", "decisionId", "status", "observedAt"],
    },
    "pipeline": [
        "INGEST",
        "NORMALIZE",
        "PROVENANCE",
        "ONTOLOGY",
        "CORRELATE",
        "SIMULATE",
        "TEVV",
        "HUMAN_GATE",
        "AUDIT",
    ],
}

SOURCE_REGISTRY: Final = [
    {
        "id": "operator",
        "name": "Authorized Operator Input",
        "mode": "AUTHORIZED",
        "provenanceRequired": True,
        "freshnessSeconds": 0,
    },
    {
        "id": "public-weather",
        "name": "Public Weather / Disaster",
        "mode": "PUBLIC",
        "provenanceRequired": True,
        "freshnessSeconds": 900,
    },
    {
        "id": "public-space",
        "name": "Public Space / Astronomy",
        "mode": "PUBLIC",
        "provenanceRequired": True,
        "freshnessSeconds": 3600,
    },
    {
        "id": "public-cyber",
        "name": "Public Defensive Cyber",
        "mode": "PUBLIC",
        "provenanceRequired": True,
        "freshnessSeconds": 3600,
    },
    {
        "id": "robot-sim",
        "name": "Authorized Robotics Simulator",
        "mode": "SIMULATION",
        "provenanceRequired": True,
        "freshnessSeconds": 5,
    },
    {
        "id": "platform-sim",
        "name": "GPT-DOUG Synthetic Event Fabric",
        "mode": "SIMULATION",
        "provenanceRequired": True,
        "freshnessSeconds": 5,
    },
]

PLATFORM_MANIFEST: Final = {
    "platform": "GPT-DOUG",
    "controlPlane": "ZYRA Intelligence Cloud",
    "ontologyVersion": ONTOLOGY_VERSION,
    "authority": "HUMAN_FIRST",
    "capabilities": [
        "persistent event store",
        "public read-only realtime stream",
        "authenticated event ingestion",
        "workspace isolation",
        "case/intel/report/alert workflow",
        "hash-chained audit evidence",
        "provenance metadata",
        "shared ontology schema",
    ],
    "blocked": sorted(BLOCKED_OPERATIONAL_EVENT_TYPES),
    "publicRealtimeClasses": sorted(PUBLIC_EVENT_CLASSES),
    "dataBoundary": (
        "Public demo streams only PUBLIC/TRAINING/SIMULATION events. "
        "FCI/CUI/NSS/classified data requires a separately approved environment."
    ),
}


def validate_event_type(value: str) -> str:
    event_type = str(value or "").strip().upper()
    if not event_type:
        raise ValueError("event_type is required")
    if event_type in BLOCKED_OPERATIONAL_EVENT_TYPES:
        raise ValueError(f"event type {event_type!r} is blocked by platform policy")
    return event_type


def validate_event_classification(value: str) -> str:
    classification = str(value or "").strip().upper()
    if classification not in ALLOWED_EVENT_CLASSES:
        raise ValueError("unsupported event classification")
    return classification
