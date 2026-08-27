"""Defensive STIX/TAXII normalization for VA3LM federal threat-intel workflows."""
from __future__ import annotations

from typing import Any, Mapping

MODE = "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
TAXII_MEDIA_TYPE = "application/taxii+json;version=2.1"


class StixIngestError(ValueError):
    pass


def build_taxii_collection_config(api_root: str, collection_id: str) -> dict[str, Any]:
    if not api_root.startswith("https://"):
        raise StixIngestError("TAXII api_root must use HTTPS")
    if not collection_id.strip():
        raise StixIngestError("collection_id is required")
    return {
        "apiRoot": api_root.rstrip("/"),
        "collectionId": collection_id.strip(),
        "mediaType": TAXII_MEDIA_TYPE,
        "operation": "READ_ONLY_INGEST",
        "mode": MODE,
        "automaticBlocking": False,
        "humanReviewRequired": True,
        "credentials": "EXTERNAL_SECRET_STORE_ONLY",
    }


def normalize_stix_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if bundle.get("type") != "bundle":
        raise StixIngestError("expected STIX bundle")
    raw_objects = bundle.get("objects", [])
    if not isinstance(raw_objects, list):
        raise StixIngestError("bundle objects must be a list")

    indicators: list[dict[str, Any]] = []
    attack_patterns: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    for obj in raw_objects:
        if not isinstance(obj, Mapping):
            continue
        object_type = obj.get("type")
        if object_type == "indicator":
            indicators.append({
                "indicatorId": str(obj.get("id", "")),
                "name": str(obj.get("name", "")),
                "pattern": str(obj.get("pattern", "")),
                "patternType": str(obj.get("pattern_type", "stix")),
                "validFrom": obj.get("valid_from"),
                "confidence": obj.get("confidence"),
                "reviewState": "UNDER_REVIEW",
                "automaticBlocking": False,
                "humanReviewRequired": True,
            })
        elif object_type == "attack-pattern":
            external_id = None
            for ref in obj.get("external_references", []) or []:
                if isinstance(ref, Mapping) and ref.get("external_id"):
                    external_id = str(ref["external_id"])
                    break
            attack_patterns.append({
                "attackPatternId": str(obj.get("id", "")),
                "name": str(obj.get("name", "")),
                "externalId": external_id,
            })
        elif object_type == "relationship":
            relationships.append({
                "relationshipId": str(obj.get("id", "")),
                "relationshipType": str(obj.get("relationship_type", "")),
                "sourceRef": str(obj.get("source_ref", "")),
                "targetRef": str(obj.get("target_ref", "")),
            })

    return {
        "mode": MODE,
        "bundleId": str(bundle.get("id", "")),
        "indicators": indicators,
        "attackPatterns": attack_patterns,
        "relationships": relationships,
        "guardrails": {
            "indicatorDefault": "INVESTIGATE_AND_VET",
            "automaticBlocking": False,
            "externalThirdPartyAction": False,
            "humanApprovalForContainment": True,
            "rawDataDefault": "REMAIN_WITH_OWNER",
        },
        "ontologyBindings": {
            "indicatorObjectType": "Indicator",
            "attackTechniqueObjectType": "AttackTechnique",
            "detectionObjectType": "Detection",
            "incidentObjectType": "Incident",
            "evidenceObjectType": "Evidence",
        },
    }
