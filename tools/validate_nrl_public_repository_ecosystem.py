#!/usr/bin/env python3
"""Validate the metadata-only U.S. Naval Research Laboratory ecosystem binding."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

MANIFEST_PATH = Path(
    "the-black-house/integrations/naval-research-laboratory/nrl-public-repository-ecosystem.json"
)
ONTOLOGY_PATH = Path("foundry/ontology/nrl-public-repository-ontology.json")
MISSION_PATH = Path("the-black-house/missions/operationdinner.json")
EXPECTED_OBSERVED_AT = "2026-09-07T22:24:49Z"
EXPECTED_SNAPSHOT_SHA256 = "f86d029840a8c3767ca7fa61ad94fe25465ccaa7b0c0276d618bb2efed575608"
EXPECTED_COUNTS = {
    "publicRepositoryCount": 58,
    "sourceRepositoryCount": 57,
    "organizationForkCount": 1,
    "activeRepositoryCount": 58,
    "archivedRepositoryCount": 0,
    "pinnedHeadCount": 57,
    "emptyRepositoryCount": 1,
}
EXPECTED_GUARDRAILS = {
    "publicMetadataOnly": True,
    "repositoryContentIngestion": False,
    "repositoryContentExecution": False,
    "cloneByDefault": False,
    "dependencyInstallation": False,
    "credentialStorage": False,
    "secretAccess": False,
    "autonomousExternalFetch": False,
    "autonomousRepositorySync": False,
    "autonomousDeployment": False,
    "externalSecurityTesting": False,
    "realWorldTargeting": False,
    "weaponsControl": False,
    "licenseReviewRequiredBeforeReuse": True,
    "semanticReviewRequiredBeforeUse": True,
    "humanReviewRequiredForExpansion": True,
    "sourceNamespaceAffiliationDoesNotTransfer": True,
    "repositoryPresenceDoesNotImplySafetyOrSupport": True,
    "governmentAffiliationInferredForGptDoug": False,
    "governmentEndorsementInferredForGptDoug": False,
    "networkEgress": "deny_by_default",
    "externalMutation": "prohibited",
    "operationalAuthority": "none",
}
EXPECTED_ONTOLOGY_GUARDRAILS = {
    "publicMetadataOnly": True,
    "manifestIsSourceOfTruth": True,
    "repositoryContentIngestion": False,
    "repositoryContentExecution": False,
    "semanticInferenceFromDescription": False,
    "cloneByDefault": False,
    "dependencyInstallation": False,
    "autonomousExternalFetch": False,
    "autonomousDeployment": False,
    "externalSecurityTesting": False,
    "realWorldTargeting": False,
    "weaponsControl": False,
    "licenseReviewRequiredBeforeReuse": True,
    "sourceCommitRequiredForDeepReview": True,
    "humanReviewRequiredForExpansion": True,
    "sourceNamespaceAffiliationDoesNotTransfer": True,
    "governmentAffiliationInferredForGptDoug": False,
    "governmentEndorsementInferredForGptDoug": False,
    "networkEgress": "deny_by_default",
    "externalMutation": "prohibited",
    "operationalAuthority": "none",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _mapping(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _array(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    return value


def _count_values(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(field) or "UNSPECIFIED"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _count_topics(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for topic in record.get("topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    return counts


def _snapshot_digest(records: list[Any]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate(
    manifest: dict[str, Any],
    ontology: Optional[dict[str, Any]] = None,
    mission: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Return every NRL integration violation without mutating the inputs."""

    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["NRL manifest root must be an object"]

    required = {
        "schemaVersion",
        "integrationId",
        "operationId",
        "controlPlane",
        "missionProtocol",
        "mode",
        "purpose",
        "observedAt",
        "repositorySnapshotSha256",
        "organization",
        "identityEvidence",
        "coverage",
        "metadataIndexes",
        "ontologyBinding",
        "repositories",
        "actions",
        "guardrails",
        "provenance",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        errors.append(f"missing required NRL manifest keys: {', '.join(missing)}")
        return errors

    exact = {
        "integrationId": "NRL_PUBLIC_REPOSITORY_ECOSYSTEM",
        "operationId": "OPERATIONDINNER",
        "controlPlane": "THE_BLACK_HOUSE_V1",
        "missionProtocol": "black-house-mission-v1",
        "mode": "PUBLIC_REPOSITORY_METADATA_AND_ONTOLOGY_ONLY",
        "observedAt": EXPECTED_OBSERVED_AT,
        "repositorySnapshotSha256": EXPECTED_SNAPSHOT_SHA256,
    }
    for key, expected in exact.items():
        if manifest.get(key) != expected:
            errors.append(f"{key} must equal {expected!r}")
    if not ISO_UTC.fullmatch(str(manifest.get("observedAt", ""))):
        errors.append("NRL observedAt must be a UTC timestamp")
    if not HEX64.fullmatch(str(manifest.get("repositorySnapshotSha256", ""))):
        errors.append("repositorySnapshotSha256 must be a SHA-256 digest")

    organization = _mapping(manifest, "organization", errors)
    expected_identity = {
        "login": "USNavalResearchLaboratory",
        "url": "https://github.com/USNavalResearchLaboratory",
        "displayName": "US Naval Research Laboratory",
        "officialSite": "https://www.nrl.navy.mil",
        "identityState": "OFFICIAL_SITE_CORROBORATED",
        "githubVerifiedBadgeState": "NOT_USED_AS_EVIDENCE",
        "archived": False,
        "publicRepositoryCountAtObservation": 58,
    }
    for key, expected in expected_identity.items():
        if organization.get(key) != expected:
            errors.append(f"organization {key!r} must equal {expected!r}")
    if "independent and unaffiliated" not in str(organization.get("affiliationBoundary", "")):
        errors.append("organization affiliation boundary must preserve GPT-DOUG independence")

    identity_evidence = _array(manifest, "identityEvidence", errors)
    official_urls = {
        item.get("url")
        for item in identity_evidence
        if isinstance(item, dict) and item.get("kind") == "official_navy_site"
    }
    if len(official_urls) < 2 or not all(
        str(url).startswith("https://www.nrl.navy.mil/") for url in official_urls
    ):
        errors.append("NRL identity requires at least two official Navy-site evidence URLs")
    if not any(
        isinstance(item, dict)
        and item.get("kind") == "github_organization_profile"
        and item.get("url") == "https://github.com/USNavalResearchLaboratory"
        for item in identity_evidence
    ):
        errors.append("NRL identity requires its GitHub organization profile evidence")

    coverage = _mapping(manifest, "coverage", errors)
    for key, expected in EXPECTED_COUNTS.items():
        if coverage.get(key) != expected:
            errors.append(f"coverage {key!r} must equal the pinned count {expected}")
    if coverage.get("completeForObservedPublicMetadata") is not True:
        errors.append("NRL coverage must state snapshot completeness")
    if coverage.get("liveSynchronization") is not False:
        errors.append("NRL integration must not claim live synchronization")

    raw_records = _array(manifest, "repositories", errors)
    records = [record for record in raw_records if isinstance(record, dict)]
    if len(records) != len(raw_records):
        errors.append("every NRL repository record must be an object")
    names: set[str] = set()
    ids: set[int] = set()
    pinned = 0
    empty = 0
    forks: list[dict[str, Any]] = []
    for record in records:
        repository = record.get("repository")
        repository_id = record.get("repositoryId")
        if not isinstance(repository, str) or not repository.startswith(
            "USNavalResearchLaboratory/"
        ):
            errors.append(f"invalid NRL repository name: {repository!r}")
        elif repository.lower() in names:
            errors.append(f"duplicate NRL repository: {repository}")
        else:
            names.add(repository.lower())
        if not isinstance(repository_id, int) or repository_id in ids:
            errors.append(f"invalid or duplicate NRL repository id: {repository_id!r}")
        else:
            ids.add(repository_id)
        if not isinstance(record.get("defaultBranch"), str) or not record["defaultBranch"]:
            errors.append(f"repository {repository} requires a default branch")
        if record.get("visibility") != "public":
            errors.append(f"repository {repository} must be public")
        if record.get("archived") is not False or record.get("disabled") is not False:
            errors.append(f"repository {repository} active state does not match snapshot")
        for field in ("createdAt", "updatedAt", "pushedAt"):
            if not ISO_UTC.fullmatch(str(record.get(field, ""))):
                errors.append(f"repository {repository} has an invalid {field}")
        topics = record.get("topics")
        if not isinstance(topics, list) or any(not isinstance(topic, str) for topic in topics):
            errors.append(f"repository {repository} topics must be strings")
        elif len(topics) != len(set(topics)):
            errors.append(f"repository {repository} has duplicate topics")

        head_state = record.get("headState")
        if head_state == "PINNED":
            pinned += 1
            if not HEX40.fullmatch(str(record.get("headSha", ""))):
                errors.append(f"repository {repository} has an invalid pinned head")
            if record.get("headError") is not None:
                errors.append(f"repository {repository} cannot have a head error when pinned")
        elif head_state == "EMPTY_REPOSITORY":
            empty += 1
            if record.get("headSha") is not None or record.get("headError") is not None:
                errors.append(f"empty repository {repository} must not claim a head or error")
            if repository != "USNavalResearchLaboratory/lstid_processing":
                errors.append(f"unexpected empty repository: {repository}")
        else:
            errors.append(f"repository {repository} has unsupported headState {head_state!r}")

        if record.get("fork") is True:
            forks.append(record)
        else:
            if record.get("directParent") is not None or record.get("directParentId") is not None:
                errors.append(f"source repository {repository} must not claim a direct parent")
            if (
                record.get("rootRepository") != repository
                or record.get("rootRepositoryId") != repository_id
            ):
                errors.append(f"source repository {repository} must be its own lineage root")

    sorted_names = sorted(names)
    record_names = [str(item.get("repository", "")).lower() for item in records]
    if record_names != sorted_names:
        errors.append("NRL repository records must remain deterministically sorted")
    if len(records) != EXPECTED_COUNTS["publicRepositoryCount"]:
        errors.append("NRL repository array length does not match coverage")
    if pinned != EXPECTED_COUNTS["pinnedHeadCount"]:
        errors.append("pinned NRL head count does not match coverage")
    if empty != EXPECTED_COUNTS["emptyRepositoryCount"]:
        errors.append("empty NRL repository count does not match coverage")
    if len(forks) != 1:
        errors.append("NRL fork count does not match coverage")
    elif (
        forks[0].get("repository") != "USNavalResearchLaboratory/code.mil"
        or forks[0].get("directParent") != "Code-dot-mil/code.mil"
        or forks[0].get("rootRepository") != "Code-dot-mil/code.mil"
    ):
        errors.append("NRL code.mil upstream lineage has drifted")

    digest = _snapshot_digest(raw_records)
    if digest != manifest.get("repositorySnapshotSha256"):
        errors.append("NRL repository snapshot digest does not match its records")

    indexes = _mapping(manifest, "metadataIndexes", errors)
    if indexes.get("primaryLanguages") != _count_values(records, "primaryLanguage"):
        errors.append("primary-language index does not match repository metadata")
    if indexes.get("declaredLicenses") != _count_values(records, "license"):
        errors.append("license index does not match repository metadata")
    if indexes.get("githubTopics") != _count_topics(records):
        errors.append("topic index does not match repository metadata")
    if indexes.get("semanticClassification") != "NOT_PERFORMED":
        errors.append("metadata index must not claim semantic classification")

    binding = _mapping(manifest, "ontologyBinding", errors)
    expected_binding = {
        "ontology": "foundry/ontology/nrl-public-repository-ontology.json",
        "state": "METADATA_GROUNDED",
        "deepSemanticReviewRequiredPerRepository": True,
    }
    if binding != expected_binding:
        errors.append("NRL ontology binding has drifted")

    actions = _array(manifest, "actions", errors)
    action_names: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            errors.append("every NRL action must be an object")
            continue
        name = action.get("apiName")
        if not isinstance(name, str) or not name or name in action_names:
            errors.append(f"invalid or duplicate NRL action: {name!r}")
            continue
        action_names.add(name)
        if action.get("networkEgress") is not False:
            errors.append(f"action {name} must deny network egress")
        if action.get("externalMutation") is not False:
            errors.append(f"action {name} must deny external mutation")
        if action.get("readOnly") is not True and action.get("requiresHumanReview") is not True:
            errors.append(f"non-read-only action {name} requires human review")
    if action_names != {
        "queryNrlRepositoryCatalog",
        "filterNrlRepositoryCatalog",
        "proposeNrlSemanticDeepDive",
    }:
        errors.append("NRL action set has drifted")

    guardrails = _mapping(manifest, "guardrails", errors)
    for key, expected in EXPECTED_GUARDRAILS.items():
        if guardrails.get(key) != expected:
            errors.append(f"guardrail {key!r} must equal {expected!r}")

    provenance = _mapping(manifest, "provenance", errors)
    if provenance.get("provider") != "GitHub REST API":
        errors.append("NRL provenance provider must remain GitHub REST API")
    if provenance.get("observedAt") != manifest.get("observedAt"):
        errors.append("NRL provenance timestamp must match the snapshot")
    if provenance.get("emptyRepositoryVerification") != (
        "lstid_processing returned an empty branch collection."
    ):
        errors.append("empty-repository provenance has drifted")

    if ontology is not None:
        _validate_ontology(ontology, manifest, records, errors)
    if mission is not None:
        _validate_mission(mission, manifest, errors)
    return errors


def _validate_ontology(
    ontology: dict[str, Any],
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if not isinstance(ontology, dict):
        errors.append("NRL ontology root must be an object")
        return
    exact = {
        "mode": "PUBLIC_REPOSITORY_METADATA_ONLY",
        "sourceManifest": (
            "the-black-house/integrations/naval-research-laboratory/"
            "nrl-public-repository-ecosystem.json"
        ),
    }
    for key, expected in exact.items():
        if ontology.get(key) != expected:
            errors.append(f"NRL ontology {key} must equal {expected!r}")
    source = ontology.get("sourceOrganization", {})
    if source.get("login") != "USNavalResearchLaboratory":
        errors.append("NRL ontology source organization has drifted")
    if source.get("identityState") != "OFFICIAL_SITE_CORROBORATED":
        errors.append("NRL ontology identity state has drifted")
    if source.get("observedAt") != manifest.get("observedAt"):
        errors.append("NRL ontology timestamp must match the source manifest")

    indexes = manifest.get("metadataIndexes", {})
    expected_materialization = {
        "ResearchOrganization": 1,
        "PublicRepository": len(records),
        "CommitSnapshot": sum(item.get("headState") == "PINNED" for item in records),
        "UpstreamRepository": sum(item.get("fork") is True for item in records),
        "ProgrammingLanguage": len(
            set(indexes.get("primaryLanguages", {})).difference({"UNSPECIFIED"})
        ),
        "LicenseDeclaration": len(
            set(indexes.get("declaredLicenses", {})).difference({"UNSPECIFIED"})
        ),
        "GitHubTopic": len(indexes.get("githubTopics", {})),
        "RepositoryLanguageLinks": sum(item.get("primaryLanguage") is not None for item in records),
        "RepositoryLicenseLinks": sum(item.get("license") is not None for item in records),
        "RepositoryTopicLinks": sum(len(item.get("topics", [])) for item in records),
    }
    if ontology.get("expectedMaterialization") != expected_materialization:
        errors.append("NRL ontology materialization counts do not match the source manifest")

    object_types = ontology.get("objectTypes", [])
    type_by_name = {item.get("apiName"): item for item in object_types if isinstance(item, dict)}
    expected_types = {
        "ResearchOrganization",
        "PublicRepository",
        "CommitSnapshot",
        "UpstreamRepository",
        "ProgrammingLanguage",
        "LicenseDeclaration",
        "GitHubTopic",
        "EvidenceSource",
        "ReviewProposal",
    }
    if set(type_by_name) != expected_types or len(type_by_name) != len(object_types):
        errors.append("NRL ontology object type set has drifted")
    for name, schema in type_by_name.items():
        if schema.get("primaryKey") not in schema.get("properties", {}):
            errors.append(f"NRL object type {name} must declare its primary key")

    link_types = ontology.get("linkTypes", [])
    link_names: set[str] = set()
    for link in link_types:
        if not isinstance(link, dict):
            errors.append("every NRL link type must be an object")
            continue
        name = link.get("apiName")
        if not isinstance(name, str) or name in link_names:
            errors.append(f"invalid or duplicate NRL link type: {name!r}")
            continue
        link_names.add(name)
        if link.get("from") not in type_by_name or link.get("to") not in type_by_name:
            errors.append(f"NRL link type {name} has an unknown endpoint type")

    mapping_rules = ontology.get("mappingRules", [])
    rule_ids = {item.get("ruleId") for item in mapping_rules if isinstance(item, dict)}
    if rule_ids != {f"NRL-MAP-{number:03d}" for number in range(1, 8)}:
        errors.append("NRL ontology mapping rule set has drifted")
    if any(item.get("outputType") not in type_by_name for item in mapping_rules):
        errors.append("NRL mapping rule references an unknown output type")

    queries = ontology.get("queryContracts", [])
    if not queries or any(item.get("readOnly") is not True for item in queries):
        errors.append("all NRL ontology query contracts must be read-only")
    actions = ontology.get("actions", [])
    for action in actions:
        name = action.get("apiName")
        if action.get("networkEgress") is not False or action.get("externalMutation") is not False:
            errors.append(f"NRL ontology action {name} must remain locally bounded")
        if action.get("readOnly") is not True and action.get("requiresHumanReview") is not True:
            errors.append(f"NRL ontology action {name} requires human review")
    if {item.get("apiName") for item in actions} != {
        "queryNrlCatalog",
        "openSemanticReviewProposal",
    }:
        errors.append("NRL ontology action set has drifted")

    ontology_guardrails = ontology.get("guardrails", {})
    for key, expected in EXPECTED_ONTOLOGY_GUARDRAILS.items():
        if ontology_guardrails.get(key) != expected:
            errors.append(f"NRL ontology guardrail {key!r} must equal {expected!r}")


def _validate_mission(mission: dict[str, Any], manifest: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(mission, dict):
        errors.append("OPERATIONDINNER mission root must be an object")
        return
    if mission.get("missionId") != "OPERATIONDINNER":
        errors.append("NRL expansion must remain bound to OPERATIONDINNER")
    if mission.get("target") != "BLACK_HOUSE_PUBLIC_DEFENSE_RESEARCH_ECOSYSTEM":
        errors.append("OPERATIONDINNER target does not include the NRL expansion")
    if mission.get("classification") != "public" or mission.get("mutation") is not False:
        errors.append("NRL mission binding must remain public and non-mutating")
    result = mission.get("result", {})
    coverage = manifest.get("coverage", {})
    count_map = {
        "nrlRepositoriesRegistered": "publicRepositoryCount",
        "nrlPinnedHeadsRegistered": "pinnedHeadCount",
        "nrlEmptyRepositoriesRegistered": "emptyRepositoryCount",
    }
    for result_key, coverage_key in count_map.items():
        if result.get(result_key) != coverage.get(coverage_key):
            errors.append(f"mission result {result_key} does not match NRL coverage")
    metadata = mission.get("metadata", {})
    if metadata.get("nrlIntegrationManifest") != (
        "the-black-house/integrations/naval-research-laboratory/"
        "nrl-public-repository-ecosystem.json"
    ):
        errors.append("mission NRL integration binding has drifted")
    if metadata.get("nrlOntology") != "foundry/ontology/nrl-public-repository-ontology.json":
        errors.append("mission NRL ontology binding has drifted")
    if result.get("externalExecutionPerformed") is not False:
        errors.append("NRL expansion must not claim external execution")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    paths = [MANIFEST_PATH, ONTOLOGY_PATH, MISSION_PATH]
    if len(sys.argv) > 1:
        paths[0] = Path(sys.argv[1])
    try:
        manifest, ontology, mission = (_load(path) for path in paths)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read NRL ecosystem artifacts: {exc}")
        return 2

    errors = validate(manifest, ontology, mission)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK: NRL ecosystem registered 58 repositories, 57 heads, and 1 empty repository")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
