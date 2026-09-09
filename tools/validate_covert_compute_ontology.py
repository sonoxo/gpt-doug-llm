#!/usr/bin/env python3
"""Fail-closed validator for the C4ADS Covert Compute public-source ontology."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("intel/supply-chain/covert-compute-c4ads-ontology.json")
EXPECTED_MODE = "PUBLIC_UNCLASSIFIED_SUPPLY_CHAIN_COMPLIANCE_ONLY"
EXPECTED_SOURCE_ID = "c4ads-covert-compute-2026-09-09"
EXPECTED_REPORT_PAGE = "https://c4ads.org/reports/covert-compute/"
EXPECTED_PDF_URL = "https://c4ads.org/wp-content/uploads/2026/09/Covert-Compute-C4ADS.pdf"
EXPECTED_PATHWAYS = {
    "direct-university-research-acquisition",
    "southeast-asia-diversion-transshipment",
    "opaque-corporate-ownership",
}
EXPECTED_GUARDRAILS = {
    "publicUnclassifiedSourcesOnly": True,
    "sourceClaimsRemainAttributed": True,
    "legalViolationInferred": False,
    "governmentAffiliationInferred": False,
    "unnamedBeneficialOwnersInferred": False,
    "sanctionsEvasionAssistance": False,
    "exportControlEvasionOptimization": False,
    "restrictedChipSupplierSourcing": False,
    "routingRecommendations": False,
    "transshipmentOptimization": False,
    "concealmentAdvice": False,
    "falseEndUserDocumentation": False,
    "credentialStorage": False,
    "automatedEnforcement": False,
    "externalMutation": False,
    "arbitraryShell": False,
    "humanReviewRequired": True,
}
EXPECTED_AGGREGATES = {
    "aggregate-direct-procurement": {
        "count": 56,
        "usdValue": 1_700_000,
        "periodStart": "2025-07",
        "periodEnd": "2026-01",
    },
    "aggregate-transshipment": {
        "count": 50,
        "usdValue": 13_400_000,
        "periodStart": "2023",
        "periodEnd": "2025",
    },
    "aggregate-megaspeed-imports": {
        "usdValue": 4_600_000_000,
        "periodStart": "2022",
        "periodEnd": "2025",
    },
}


def _mapping(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _list(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    return value


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ontology root must be an object"]

    required = {
        "name",
        "version",
        "mode",
        "deploymentState",
        "purpose",
        "sourceSnapshot",
        "interpretationRules",
        "objectTypes",
        "linkTypes",
        "evidence",
        "objects",
        "links",
        "actions",
        "guardrails",
    }
    missing = sorted(required.difference(data))
    if missing:
        errors.append(f"missing required top-level keys: {', '.join(missing)}")
        return errors

    if data.get("mode") != EXPECTED_MODE:
        errors.append(f"mode must remain {EXPECTED_MODE}")

    snapshot = _mapping(data, "sourceSnapshot", errors)
    if snapshot.get("sourceId") != EXPECTED_SOURCE_ID:
        errors.append("sourceSnapshot.sourceId drift")
    if snapshot.get("reportPage") != EXPECTED_REPORT_PAGE:
        errors.append("sourceSnapshot.reportPage drift")
    if snapshot.get("pdfUrl") != EXPECTED_PDF_URL:
        errors.append("sourceSnapshot.pdfUrl drift")
    if snapshot.get("sourceClass") != "PUBLIC_UNCLASSIFIED_REPORT":
        errors.append("sourceSnapshot.sourceClass must remain PUBLIC_UNCLASSIFIED_REPORT")
    if "cache miss" not in str(snapshot.get("coverageNote", "")).lower():
        errors.append("coverageNote must preserve the PDF-ingestion limitation")

    rules = _mapping(data, "interpretationRules", errors)
    if rules.get("sourceClaims") != "ATTRIBUTE_TO_C4ADS":
        errors.append("sourceClaims must remain attributed to C4ADS")
    if rules.get("ownershipLinks") != "DO_NOT_INFER_UNNAMED_BENEFICIAL_OWNERS":
        errors.append("ownershipLinks must prohibit unnamed-owner inference")
    if rules.get("operationalAuthority") != "NONE":
        errors.append("operationalAuthority must remain NONE")

    if data.get("guardrails") != EXPECTED_GUARDRAILS:
        errors.append("guardrails have drifted from the fail-closed compliance profile")

    evidence = _list(data, "evidence", errors)
    evidence_ids: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict):
            errors.append("every evidence record must be an object")
            continue
        evidence_id = item.get("evidenceId")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append("evidence record has invalid evidenceId")
            continue
        if evidence_id in evidence_ids:
            errors.append(f"duplicate evidenceId: {evidence_id}")
        evidence_ids.add(evidence_id)
        if not isinstance(item.get("summary"), str) or not item["summary"].strip():
            errors.append(f"evidence {evidence_id} requires a summary")
        if item.get("claimNature") not in {"source_statement", "derived_compliance_mapping"}:
            errors.append(f"evidence {evidence_id} has unsupported claimNature")

    object_types = _list(data, "objectTypes", errors)
    type_by_name: dict[str, dict[str, Any]] = {}
    for schema in object_types:
        if not isinstance(schema, dict):
            errors.append("every objectType must be an object")
            continue
        name = schema.get("apiName")
        if not isinstance(name, str) or not name or name in type_by_name:
            errors.append(f"invalid or duplicate objectType: {name!r}")
            continue
        type_by_name[name] = schema
        props = schema.get("properties")
        if not isinstance(props, dict) or schema.get("primaryKey") not in props:
            errors.append(f"objectType {name} must declare its primary-key property")

    link_types = _list(data, "linkTypes", errors)
    link_type_by_name: dict[str, dict[str, Any]] = {}
    for schema in link_types:
        if not isinstance(schema, dict):
            errors.append("every linkType must be an object")
            continue
        name = schema.get("apiName")
        if not isinstance(name, str) or not name or name in link_type_by_name:
            errors.append(f"invalid or duplicate linkType: {name!r}")
            continue
        link_type_by_name[name] = schema
        if schema.get("from") not in type_by_name or schema.get("to") not in type_by_name:
            errors.append(f"linkType {name} references an unknown object type")

    objects = _list(data, "objects", errors)
    object_by_id: dict[str, dict[str, Any]] = {}
    for obj in objects:
        if not isinstance(obj, dict):
            errors.append("every object must be an object")
            continue
        object_id = obj.get("id")
        obj_type = obj.get("type")
        props = obj.get("properties")
        refs = obj.get("evidenceIds")
        if not isinstance(object_id, str) or not object_id or object_id in object_by_id:
            errors.append(f"invalid or duplicate object id: {object_id!r}")
            continue
        object_by_id[object_id] = obj
        schema = type_by_name.get(str(obj_type))
        if schema is None:
            errors.append(f"object {object_id} references unknown type {obj_type!r}")
        elif not isinstance(props, dict):
            errors.append(f"object {object_id} properties must be an object")
        else:
            pk = schema["primaryKey"]
            if props.get(pk) != object_id:
                errors.append(f"object {object_id} primary key must match its id")
            unknown_props = sorted(set(props).difference(schema.get("properties", {})))
            if unknown_props:
                errors.append(f"object {object_id} has undeclared properties: {', '.join(unknown_props)}")
        if not isinstance(refs, list) or not refs:
            errors.append(f"object {object_id} requires evidenceIds")
        elif any(ref not in evidence_ids for ref in refs):
            errors.append(f"object {object_id} references unknown evidence")

    pathways = {
        object_id
        for object_id, obj in object_by_id.items()
        if obj.get("type") == "AcquisitionPathway"
    }
    if pathways != EXPECTED_PATHWAYS:
        errors.append("AcquisitionPathway set has drifted from the three C4ADS pathways")

    for aggregate_id, expected in EXPECTED_AGGREGATES.items():
        obj = object_by_id.get(aggregate_id, {})
        if obj.get("type") != "TradeAggregate":
            errors.append(f"missing TradeAggregate: {aggregate_id}")
            continue
        props = obj.get("properties", {})
        for key, expected_value in expected.items():
            if props.get(key) != expected_value:
                errors.append(f"{aggregate_id}.{key} must equal {expected_value!r}")

    megaspeed = object_by_id.get("megaspeed-international-pte-ltd", {})
    if megaspeed.get("type") != "Organization":
        errors.append("Megaspeed must remain an attributed Organization object")
    if "C4ADS cites third-party reporting" not in str(megaspeed.get("properties", {}).get("sourceCharacterization", "")):
        errors.append("Megaspeed characterization must preserve third-party attribution")

    links = _list(data, "links", errors)
    link_ids: set[str] = set()
    for link in links:
        if not isinstance(link, dict):
            errors.append("every link must be an object")
            continue
        link_id = link.get("id")
        relation = link.get("type")
        source = link.get("from")
        target = link.get("to")
        refs = link.get("evidenceIds")
        if not isinstance(link_id, str) or not link_id or link_id in link_ids:
            errors.append(f"invalid or duplicate link id: {link_id!r}")
            continue
        link_ids.add(link_id)
        schema = link_type_by_name.get(str(relation))
        if schema is None:
            errors.append(f"link {link_id} references unknown link type")
            continue
        if source not in object_by_id or target not in object_by_id:
            errors.append(f"link {link_id} has a dangling endpoint")
            continue
        if object_by_id[source].get("type") != schema.get("from"):
            errors.append(f"link {link_id} source type mismatch")
        if object_by_id[target].get("type") != schema.get("to"):
            errors.append(f"link {link_id} target type mismatch")
        if not isinstance(refs, list) or not refs or any(ref not in evidence_ids for ref in refs):
            errors.append(f"link {link_id} requires valid evidenceIds")

    actions = _list(data, "actions", errors)
    for action in actions:
        if not isinstance(action, dict):
            errors.append("every action must be an object")
            continue
        name = action.get("apiName")
        if action.get("externalMutation") is not False:
            errors.append(f"action {name} must keep externalMutation=false")
        description = str(action.get("description", "")).lower()
        prohibited = ("source restricted chips", "evade export", "optimize transshipment", "conceal shipment")
        if any(term in description for term in prohibited):
            errors.append(f"action {name} contains prohibited operational guidance")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to read ontology: {exc}")
        return 1

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: C4ADS Covert Compute ontology is source-attributed and fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
