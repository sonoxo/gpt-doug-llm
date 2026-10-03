#!/usr/bin/env python3
"""Fail-closed validation for the LLMs-at-DoD public reference ontology."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("foundry/ontology/llms-at-dod-ontology.json")
EXPECTED_MODE = "PUBLIC_UNCLASSIFIED_REFERENCE_ONLY"
EXPECTED_COMMIT = "fc90483ae3a2db48d46eb3231eccf691cec6d346"
EXPECTED_ARTIFACTS = {
    "source-readme": {
        "path": "README.md",
        "gitBlobSha": "6acdd4900f53832cc3ba4a865ae9aa73e4d680fb",
        "sha256": "6143d734f6752530c984b3736ed98f61d086ea3dc6822e8cac34cfdd03ec583f",
        "cellCount": 0,
    },
    "source-open-source-getting-started": {
        "path": "tutorials/Open_Source_LLMs_Getting_Started.ipynb",
        "gitBlobSha": "809b754a165d2045d120d46a04c407b572d60a8e",
        "sha256": "1f454d9d248d66171b82ad990c3c8a9e95bd659841187111a940f7193cb5c66b",
        "cellCount": 16,
    },
    "source-chatting-with-docs": {
        "path": "tutorials/Chatting with your Docs.ipynb",
        "gitBlobSha": "4ba5f0f3056d4a4dd4ffb768e3d829e6f5e7a8c8",
        "sha256": "ceb75388e853dbbe88d331574cbaf5d2a842f4d0ddf6e2cc46b4749aa39232c1",
        "cellCount": 32,
    },
    "source-axon-fine-tune": {
        "path": "axon/axon-fine-tune.ipynb",
        "gitBlobSha": "5b15046c6ebe9126da2f518dcccc336f3ceaf5bb",
        "sha256": "6ddc87c39d5fd28271c75cbe411d5d4d37a2b16bd7a33f4aeaf491c6ff282d67",
        "cellCount": 41,
    },
    "source-scrape-docs": {
        "path": "axon/scrape_docs_gen_dataset.ipynb",
        "gitBlobSha": "722c5e36e5dfecb30a9fc8d0d84a2d512996338b",
        "sha256": "b4a1699ec6e8156e32e88b3ea5f18a0dff0badd879bab20a7c169666ed373d1c",
        "cellCount": 17,
    },
}
EXPECTED_INTERPRETATION_RULES = {
    "sourceClaims": "ATTRIBUTE_NOT_ADOPT",
    "structuralMappings": "DERIVED_FROM_CITED_SOURCE",
    "forkLineage": "DISTINGUISH_OBSERVED_FORK_FROM_UPSTREAM",
    "governmentStatus": "NEVER_INFER",
    "operationalAuthority": "NONE",
}
EXPECTED_GUARDRAILS = {
    "publicUnclassifiedSourcesOnly": True,
    "classifiedDataIngestion": False,
    "credentialStorage": False,
    "sourceCodeExecution": "prohibited_by_ontology",
    "autonomousExternalFetch": False,
    "autonomousModelTraining": False,
    "autonomousModelPublishing": False,
    "humanReviewForRefresh": True,
    "sourceClaimsRemainAttributed": True,
    "governmentAffiliationInferred": False,
    "governmentAuthorizationInferred": False,
    "officialEndorsementInferred": False,
    "networkEgress": "deny_by_default",
    "externalMutation": "prohibited",
    "operationalAuthority": "none",
}
ALLOWED_CLAIM_NATURES = {
    "observed_metadata",
    "source_statement",
    "source_code",
    "notebook_authored_claim",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _required_mapping(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _required_list(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    return value


def validate(data: dict[str, Any]) -> list[str]:
    """Return every ontology contract violation without mutating *data*."""

    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ontology root must be an object"]

    required = {
        "name",
        "version",
        "mode",
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
    if not isinstance(data.get("purpose"), str) or not data["purpose"].strip():
        errors.append("purpose must be a non-empty string")

    snapshot = _required_mapping(data, "sourceSnapshot", errors)
    observed = snapshot.get("observedRepository", {})
    upstream = snapshot.get("upstreamRepository", {})
    lineage = snapshot.get("forkLineage", {})
    commit = snapshot.get("commit", {})
    if observed.get("fullName") != "sonoxo/LLMs-at-DoD":
        errors.append("observedRepository must remain sonoxo/LLMs-at-DoD")
    if observed.get("role") != "OBSERVED_FORK":
        errors.append("observedRepository role must remain OBSERVED_FORK")
    if upstream.get("fullName") != "deptofdefense/LLMs-at-DoD":
        errors.append("upstreamRepository must remain deptofdefense/LLMs-at-DoD")
    if upstream.get("role") != "UPSTREAM_SOURCE":
        errors.append("upstreamRepository role must remain UPSTREAM_SOURCE")
    if upstream.get("archivedAtObservation") is not True:
        errors.append("upstreamRepository must preserve archivedAtObservation=true")
    if lineage != {"isFork": True, "parent": "deptofdefense/LLMs-at-DoD"}:
        errors.append("forkLineage must preserve the verified direct parent")
    if commit.get("sha") != EXPECTED_COMMIT:
        errors.append(f"source commit must remain pinned to {EXPECTED_COMMIT}")
    if not HEX40.fullmatch(str(commit.get("sha", ""))):
        errors.append("source commit SHA must be 40 lowercase hexadecimal characters")

    artifacts = _required_list(snapshot, "evidenceArtifacts", errors)
    artifact_by_id: dict[str, dict[str, Any]] = {}
    paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("every evidenceArtifact must be an object")
            continue
        artifact_id = artifact.get("artifactId")
        path = artifact.get("path")
        if not isinstance(artifact_id, str) or artifact_id in artifact_by_id:
            errors.append(f"invalid or duplicate evidence artifact id: {artifact_id!r}")
            continue
        artifact_by_id[artifact_id] = artifact
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
            errors.append(f"artifact {artifact_id} has an unsafe path")
        elif path in paths:
            errors.append(f"duplicate evidence artifact path: {path}")
        else:
            paths.add(path)
        if not HEX40.fullmatch(str(artifact.get("gitBlobSha", ""))):
            errors.append(f"artifact {artifact_id} has an invalid gitBlobSha")
        if not HEX64.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"artifact {artifact_id} has an invalid sha256")
        if not isinstance(artifact.get("cellCount"), int) or artifact["cellCount"] < 0:
            errors.append(f"artifact {artifact_id} has an invalid cellCount")

    if set(artifact_by_id) != set(EXPECTED_ARTIFACTS):
        errors.append("source snapshot evidence artifact set has drifted")
    for artifact_id, expected in EXPECTED_ARTIFACTS.items():
        actual = artifact_by_id.get(artifact_id, {})
        for key, expected_value in expected.items():
            if actual.get(key) != expected_value:
                errors.append(f"artifact {artifact_id} field {key} must equal {expected_value!r}")

    if data.get("interpretationRules") != EXPECTED_INTERPRETATION_RULES:
        errors.append(
            "interpretationRules must preserve source attribution and authority boundaries"
        )

    object_types = _required_list(data, "objectTypes", errors)
    type_by_name: dict[str, dict[str, Any]] = {}
    for item in object_types:
        if not isinstance(item, dict):
            errors.append("every objectType must be an object")
            continue
        name = item.get("apiName")
        primary_key = item.get("primaryKey")
        properties = item.get("properties")
        if not isinstance(name, str) or not name or name in type_by_name:
            errors.append(f"invalid or duplicate object type: {name!r}")
            continue
        type_by_name[name] = item
        if not isinstance(properties, dict) or primary_key not in properties:
            errors.append(f"object type {name} must declare its primary key property")

    link_types = _required_list(data, "linkTypes", errors)
    link_type_by_name: dict[str, dict[str, Any]] = {}
    for item in link_types:
        if not isinstance(item, dict):
            errors.append("every linkType must be an object")
            continue
        name = item.get("apiName")
        if not isinstance(name, str) or not name or name in link_type_by_name:
            errors.append(f"invalid or duplicate link type: {name!r}")
            continue
        link_type_by_name[name] = item
        if item.get("from") not in type_by_name:
            errors.append(f"link type {name} references unknown source object type")
        if item.get("to") not in type_by_name:
            errors.append(f"link type {name} references unknown target object type")

    evidence_records = _required_list(data, "evidence", errors)
    evidence_ids: set[str] = set()
    for record in evidence_records:
        if not isinstance(record, dict):
            errors.append("every evidence record must be an object")
            continue
        evidence_id = record.get("evidenceId")
        if not isinstance(evidence_id, str) or not evidence_id or evidence_id in evidence_ids:
            errors.append(f"invalid or duplicate evidence id: {evidence_id!r}")
            continue
        evidence_ids.add(evidence_id)
        source_kind = record.get("sourceKind")
        source_id = record.get("sourceId")
        locator = record.get("locator")
        if record.get("claimNature") not in ALLOWED_CLAIM_NATURES:
            errors.append(f"evidence {evidence_id} has an unsupported claimNature")
        if not isinstance(locator, dict) or not locator:
            errors.append(f"evidence {evidence_id} requires a locator")
            continue
        if source_kind == "repository_metadata":
            if source_id not in {"observedRepository", "upstreamRepository", "commit"}:
                errors.append(f"evidence {evidence_id} has an unknown metadata source")
            if not isinstance(locator.get("field"), str):
                errors.append(f"metadata evidence {evidence_id} requires a field locator")
        elif source_kind == "tracked_file":
            artifact = artifact_by_id.get(str(source_id))
            if artifact is None:
                errors.append(f"evidence {evidence_id} references an unknown artifact")
                continue
            if artifact.get("cellCount", 0) > 0:
                cells = locator.get("cells")
                if not isinstance(cells, list) or not cells:
                    errors.append(f"notebook evidence {evidence_id} requires cell locators")
                elif any(
                    not isinstance(cell, int) or cell < 0 or cell >= artifact["cellCount"]
                    for cell in cells
                ):
                    errors.append(f"notebook evidence {evidence_id} has an out-of-range cell")
            elif not isinstance(locator.get("section"), str):
                errors.append(f"text evidence {evidence_id} requires a section locator")
        else:
            errors.append(f"evidence {evidence_id} has an unsupported sourceKind")

    objects = _required_list(data, "objects", errors)
    object_by_id: dict[str, dict[str, Any]] = {}
    for obj in objects:
        if not isinstance(obj, dict):
            errors.append("every object must be an object")
            continue
        object_id = obj.get("id")
        object_type = obj.get("type")
        properties = obj.get("properties")
        refs = obj.get("evidenceIds")
        if not isinstance(object_id, str) or not object_id or object_id in object_by_id:
            errors.append(f"invalid or duplicate object id: {object_id!r}")
            continue
        object_by_id[object_id] = obj
        schema = type_by_name.get(str(object_type))
        if schema is None:
            errors.append(f"object {object_id} references unknown type {object_type!r}")
        elif not isinstance(properties, dict):
            errors.append(f"object {object_id} properties must be an object")
        else:
            primary_key = schema["primaryKey"]
            if properties.get(primary_key) != object_id:
                errors.append(f"object {object_id} primary key must match its id")
            unknown = sorted(set(properties).difference(schema.get("properties", {})))
            if unknown:
                errors.append(f"object {object_id} has undeclared properties: {', '.join(unknown)}")
        if not isinstance(refs, list) or not refs:
            errors.append(f"object {object_id} requires evidenceIds")
        elif any(ref not in evidence_ids for ref in refs):
            errors.append(f"object {object_id} references unknown evidence")

    source_artifact_objects = {
        object_id: obj
        for object_id, obj in object_by_id.items()
        if obj.get("type") == "SourceArtifact"
    }
    if set(source_artifact_objects) != set(EXPECTED_ARTIFACTS):
        errors.append("SourceArtifact object set must match the pinned evidence artifacts")
    for artifact_id, artifact in artifact_by_id.items():
        obj_properties = source_artifact_objects.get(artifact_id, {}).get("properties", {})
        for field in ("path", "mediaType", "gitBlobSha", "sha256", "cellCount"):
            if obj_properties.get(field) != artifact.get(field):
                errors.append(f"SourceArtifact {artifact_id} does not match snapshot field {field}")

    links = _required_list(data, "links", errors)
    link_ids: set[str] = set()
    triples: set[tuple[str, str, str]] = set()
    for link in links:
        if not isinstance(link, dict):
            errors.append("every link must be an object")
            continue
        link_id = link.get("id")
        relation = link.get("type")
        source_id = link.get("from")
        target_id = link.get("to")
        refs = link.get("evidenceIds")
        if not isinstance(link_id, str) or not link_id or link_id in link_ids:
            errors.append(f"invalid or duplicate link id: {link_id!r}")
            continue
        link_ids.add(link_id)
        relation_schema = link_type_by_name.get(str(relation))
        source_obj = object_by_id.get(str(source_id))
        target_obj = object_by_id.get(str(target_id))
        if relation_schema is None:
            errors.append(f"link {link_id} references unknown link type")
        if source_obj is None or target_obj is None:
            errors.append(f"link {link_id} has a dangling endpoint")
        elif relation_schema is not None and (
            source_obj.get("type") != relation_schema.get("from")
            or target_obj.get("type") != relation_schema.get("to")
        ):
            errors.append(f"link {link_id} endpoint types do not match {relation}")
        triple = (str(relation), str(source_id), str(target_id))
        if triple in triples:
            errors.append(f"duplicate semantic link: {triple}")
        triples.add(triple)
        if not isinstance(refs, list) or not refs:
            errors.append(f"link {link_id} requires evidenceIds")
        elif any(ref not in evidence_ids for ref in refs):
            errors.append(f"link {link_id} references unknown evidence")

    used_evidence = {
        ref
        for entity in [*objects, *links]
        if isinstance(entity, dict) and isinstance(entity.get("evidenceIds"), list)
        for ref in entity["evidenceIds"]
    }
    orphaned = sorted(evidence_ids.difference(used_evidence))
    if orphaned:
        errors.append(f"orphaned evidence records: {', '.join(orphaned)}")

    actions = _required_list(data, "actions", errors)
    action_names: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            errors.append("every action must be an object")
            continue
        name = action.get("apiName")
        if not isinstance(name, str) or not name or name in action_names:
            errors.append(f"invalid or duplicate action: {name!r}")
            continue
        action_names.add(name)
        if action.get("objectType") not in type_by_name:
            errors.append(f"action {name} references an unknown objectType")
        if action.get("externalMutation") is not False:
            errors.append(f"action {name} must prohibit external mutation")
        if action.get("networkEgress") is not False:
            errors.append(f"action {name} must prohibit network egress")
        if action.get("readOnly") is not True and action.get("requiresHumanReview") is not True:
            errors.append(f"non-read-only action {name} requires human review")
    expected_actions = {"queryReferenceGraph", "verifySourceSnapshot", "proposeSourceRefresh"}
    if action_names != expected_actions:
        errors.append("ontology action set has drifted from its bounded contract")

    guardrails = _required_mapping(data, "guardrails", errors)
    for key, expected in EXPECTED_GUARDRAILS.items():
        if guardrails.get(key) != expected:
            errors.append(f"guardrail {key!r} must equal {expected!r}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read ontology: {exc}")
        return 2

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {path} passed LLMs-at-DoD ontology validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
