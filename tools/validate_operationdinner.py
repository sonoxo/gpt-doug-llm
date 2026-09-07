#!/usr/bin/env python3
"""Validate the bounded OPERATIONDINNER Black House fork ecosystem."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

MANIFEST_PATH = Path(
    "the-black-house/integrations/deptofdefense/operationdinner-fork-ecosystem.json"
)
MISSION_PATH = Path("the-black-house/missions/operationdinner.json")
ONTOLOGY_PATH = Path("foundry/ontology/llms-at-dod-ontology.json")
EXPECTED_OBSERVED_AT = "2026-09-07T22:07:51Z"
EXPECTED_LINEAGE_SHA256 = "59ca2bc1509b3d37046f622bc37f7a3e012a5e0bbdd09d8ce2822923cc72db3d"
EXPECTED_COUNTS = {
    "sourceOrganizationRepositoryCount": 63,
    "sourceOrganizationForkCount": 8,
    "verifiedSonoxoForkCount": 38,
    "notPresentAsVerifiedSonoxoForkCount": 25,
}
EXPECTED_SOURCE_ORG_FORK_PARENTS = {
    "deptofdefense/certificate-transparency": "google/certificate-transparency",
    "deptofdefense/combee": "zeetwii/combee",
    "deptofdefense/crossfeed-ows": "cisagov/crossfeed",
    "deptofdefense/naruto": "zeetwii/naruto",
    "deptofdefense/send": "mozilla/send",
    "deptofdefense/telepath": "isears/telepath",
    "deptofdefense/terraform-provisioner-ansible": ("jonmorehouse/terraform-provisioner-ansible"),
    "deptofdefense/traefik": "traefik/traefik",
}
EXPECTED_GUARDRAILS = {
    "publicMetadataOnly": True,
    "repositoryContentExecution": False,
    "cloneByDefault": False,
    "dependencyInstallation": False,
    "credentialStorage": False,
    "secretAccess": False,
    "githubWrites": False,
    "autonomousForkCreation": False,
    "autonomousRepositorySync": False,
    "autonomousExternalFetch": False,
    "licenseReviewRequiredBeforeReuse": True,
    "humanReviewRequiredForRefresh": True,
    "archivedStatusDoesNotImplySafetyOrSupport": True,
    "lineageDoesNotTransferAuthorization": True,
    "governmentAffiliationInferred": False,
    "governmentEndorsementInferred": False,
    "networkEgress": "deny_by_default",
    "externalMutation": "prohibited",
    "operationalAuthority": "none",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
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


def validate(
    manifest: dict[str, Any],
    mission: Optional[dict[str, Any]] = None,
    ontology: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Return all OPERATIONDINNER contract violations."""

    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["integration manifest root must be an object"]

    required = {
        "schemaVersion",
        "operationId",
        "controlPlane",
        "missionProtocol",
        "mode",
        "purpose",
        "observedAt",
        "lineageSnapshotSha256",
        "sourceOrganization",
        "forkOwner",
        "scope",
        "ontologyBindings",
        "sourceOrganizationForks",
        "verifiedSonoxoForks",
        "notPresentAsVerifiedSonoxoFork",
        "actions",
        "guardrails",
        "provenance",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        errors.append(f"missing required manifest keys: {', '.join(missing)}")
        return errors

    exact_fields = {
        "operationId": "OPERATIONDINNER",
        "controlPlane": "THE_BLACK_HOUSE_V1",
        "missionProtocol": "black-house-mission-v1",
        "mode": "PUBLIC_METADATA_AND_ONTOLOGY_ONLY",
        "observedAt": EXPECTED_OBSERVED_AT,
        "lineageSnapshotSha256": EXPECTED_LINEAGE_SHA256,
    }
    for key, expected in exact_fields.items():
        if manifest.get(key) != expected:
            errors.append(f"{key} must equal {expected!r}")
    if not ISO_UTC.fullmatch(str(manifest.get("observedAt", ""))):
        errors.append("observedAt must be a UTC timestamp")
    if not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("lineageSnapshotSha256", ""))):
        errors.append("lineageSnapshotSha256 must be a SHA-256 digest")

    source_org = _mapping(manifest, "sourceOrganization", errors)
    expected_source_identity = {
        "login": "deptofdefense",
        "url": "https://github.com/deptofdefense",
        "profileOrganization": "Defense Digital Service",
        "githubVerified": True,
        "verifiedDomain": "dds.mil",
        "archived": True,
        "archivedOn": "2025-05-07",
        "publicRepositoryCountAtObservation": 63,
    }
    for key, expected in expected_source_identity.items():
        if source_org.get(key) != expected:
            errors.append(f"sourceOrganization {key!r} must equal {expected!r}")

    fork_owner = _mapping(manifest, "forkOwner", errors)
    if fork_owner.get("login") != "sonoxo":
        errors.append("forkOwner must remain sonoxo")
    if fork_owner.get("relationship") != "INDEPENDENT_FORK_OWNER":
        errors.append("forkOwner relationship must remain independent")
    if fork_owner.get("officialDoDStatus") is not False:
        errors.append("sonoxo forks must never be labeled official DoD repositories")

    scope = _mapping(manifest, "scope", errors)
    for key, expected in EXPECTED_COUNTS.items():
        if scope.get(key) != expected:
            errors.append(f"scope {key!r} must equal the pinned count {expected}")
    if scope.get("snapshotCompleteness") != "COMPLETE_FOR_OBSERVED_PUBLIC_METADATA":
        errors.append("snapshot completeness state has drifted")
    if scope.get("liveSynchronization") is not False:
        errors.append("OPERATIONDINNER must not claim live synchronization")

    source_forks = _array(manifest, "sourceOrganizationForks", errors)
    source_fork_names: set[str] = set()
    source_fork_ids: set[int] = set()
    for item in source_forks:
        if not isinstance(item, dict):
            errors.append("every sourceOrganizationFork must be an object")
            continue
        repository = item.get("repository")
        repository_id = item.get("repositoryId")
        parent = item.get("directParent")
        if not isinstance(repository, str) or repository in source_fork_names:
            errors.append(f"invalid or duplicate source-organization fork: {repository!r}")
        else:
            source_fork_names.add(repository)
        if not isinstance(repository_id, int) or repository_id in source_fork_ids:
            errors.append(
                f"invalid or duplicate source-organization repository id: {repository_id!r}"
            )
        else:
            source_fork_ids.add(repository_id)
        if EXPECTED_SOURCE_ORG_FORK_PARENTS.get(str(repository)) != parent:
            errors.append(f"source-organization fork {repository} has incorrect upstream parent")
        if item.get("rootRepository") != parent:
            errors.append(
                f"source-organization fork {repository} must preserve its root repository"
            )
        if item.get("archivedAtObservation") is not True:
            errors.append(f"source-organization fork {repository} must remain archived in snapshot")
        if not HEX40.fullmatch(str(item.get("headSha", ""))):
            errors.append(f"source-organization fork {repository} has an invalid head SHA")
    if source_fork_names != set(EXPECTED_SOURCE_ORG_FORK_PARENTS):
        errors.append("source-organization fork set has drifted")

    verified_forks = _array(manifest, "verifiedSonoxoForks", errors)
    fork_names: set[str] = set()
    fork_ids: set[int] = set()
    parent_names: set[str] = set()
    parent_ids: set[int] = set()
    for item in verified_forks:
        if not isinstance(item, dict):
            errors.append("every verifiedSonoxoFork must be an object")
            continue
        fork = item.get("forkRepository")
        fork_id = item.get("forkRepositoryId")
        parent = item.get("directParent")
        parent_id = item.get("directParentId")
        root = item.get("rootRepository")
        if not isinstance(fork, str) or not fork.startswith("sonoxo/"):
            errors.append(f"invalid sonoxo fork name: {fork!r}")
        elif fork.lower() in fork_names:
            errors.append(f"duplicate sonoxo fork: {fork}")
        else:
            fork_names.add(fork.lower())
        if not isinstance(parent, str) or not parent.startswith("deptofdefense/"):
            errors.append(f"fork {fork} must have a deptofdefense direct parent")
        else:
            parent_names.add(parent.lower())
        if isinstance(fork, str) and isinstance(parent, str):
            if fork.split("/", 1)[-1].lower() != parent.split("/", 1)[-1].lower():
                errors.append(f"fork {fork} and parent {parent} repository names do not match")
        if not isinstance(root, str) or "/" not in root:
            errors.append(f"fork {fork} requires a transitive root repository")
        if not isinstance(fork_id, int) or fork_id in fork_ids:
            errors.append(f"invalid or duplicate sonoxo fork id: {fork_id!r}")
        else:
            fork_ids.add(fork_id)
        if not isinstance(parent_id, int) or parent_id in parent_ids:
            errors.append(f"invalid or duplicate direct parent id: {parent_id!r}")
        else:
            parent_ids.add(parent_id)
        if item.get("visibility") != "public":
            errors.append(f"fork {fork} must be public in this public-only snapshot")
        if item.get("forkArchived") is not False:
            errors.append(f"fork {fork} archived state does not match snapshot")
        if item.get("sourceArchivedAtObservation") is not True:
            errors.append(f"fork {fork} must preserve its parent's archived state")
        if not HEX40.fullmatch(str(item.get("forkHeadSha", ""))):
            errors.append(f"fork {fork} has an invalid pinned head SHA")
        if not ISO_UTC.fullmatch(str(item.get("forkCreatedAt", ""))):
            errors.append(f"fork {fork} has an invalid creation timestamp")

    absent = _array(manifest, "notPresentAsVerifiedSonoxoFork", errors)
    absent_names: set[str] = set()
    absent_ids: set[int] = set()
    for item in absent:
        if not isinstance(item, dict):
            errors.append("every coverage-gap record must be an object")
            continue
        repository = item.get("repository")
        repository_id = item.get("repositoryId")
        if not isinstance(repository, str) or not repository.startswith("deptofdefense/"):
            errors.append(f"invalid coverage-gap repository: {repository!r}")
        else:
            absent_names.add(repository.lower())
        if not isinstance(repository_id, int) or repository_id in absent_ids:
            errors.append(f"invalid or duplicate coverage-gap id: {repository_id!r}")
        else:
            absent_ids.add(repository_id)
        if item.get("archivedAtObservation") is not True:
            errors.append(f"coverage-gap repository {repository} must preserve archived state")

    if len(source_forks) != EXPECTED_COUNTS["sourceOrganizationForkCount"]:
        errors.append("sourceOrganizationForks length does not match scope")
    if len(verified_forks) != EXPECTED_COUNTS["verifiedSonoxoForkCount"]:
        errors.append("verifiedSonoxoForks length does not match scope")
    if len(absent) != EXPECTED_COUNTS["notPresentAsVerifiedSonoxoForkCount"]:
        errors.append("coverage-gap length does not match scope")
    if parent_names.intersection(absent_names):
        errors.append("a source repository cannot be both verified and a coverage gap")
    if (
        len(parent_names.union(absent_names))
        != EXPECTED_COUNTS["sourceOrganizationRepositoryCount"]
    ):
        errors.append(
            "verified parents and coverage gaps do not cover the pinned source organization"
        )
    if not source_fork_names.issubset(parent_names.union(absent_names)):
        errors.append("source-organization forks must belong to the source inventory")

    lineage_payload = {
        "sourceOrganizationForks": source_forks,
        "verifiedSonoxoForks": verified_forks,
        "notPresentAsVerifiedSonoxoFork": absent,
    }
    lineage_json = json.dumps(lineage_payload, ensure_ascii=False, separators=(",", ":"))
    lineage_digest = hashlib.sha256(lineage_json.encode("utf-8")).hexdigest()
    if lineage_digest != manifest.get("lineageSnapshotSha256"):
        errors.append("OPERATIONDINNER lineage snapshot digest does not match its records")

    bindings = _array(manifest, "ontologyBindings", errors)
    expected_binding = {
        "repository": "sonoxo/LLMs-at-DoD",
        "forkHeadSha": "fc90483ae3a2db48d46eb3231eccf691cec6d346",
        "ontology": "foundry/ontology/llms-at-dod-ontology.json",
        "state": "SOURCE_GROUNDED",
    }
    if bindings != [expected_binding]:
        errors.append("LLMs-at-DoD ontology binding has drifted")
    llm_record = next(
        (
            item
            for item in verified_forks
            if item.get("forkRepository") == expected_binding["repository"]
        ),
        None,
    )
    if llm_record is None or llm_record.get("forkHeadSha") != expected_binding["forkHeadSha"]:
        errors.append("LLMs-at-DoD fork record does not match its ontology binding")

    actions = _array(manifest, "actions", errors)
    action_names: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            errors.append("every OPERATIONDINNER action must be an object")
            continue
        name = action.get("apiName")
        if not isinstance(name, str) or not name or name in action_names:
            errors.append(f"invalid or duplicate action: {name!r}")
            continue
        action_names.add(name)
        if action.get("networkEgress") is not False:
            errors.append(f"action {name} must deny network egress")
        if action.get("externalMutation") is not False:
            errors.append(f"action {name} must deny external mutation")
        if action.get("readOnly") is not True and action.get("requiresHumanReview") is not True:
            errors.append(f"non-read-only action {name} requires human review")
    if action_names != {
        "queryPinnedForkGraph",
        "compareUserSuppliedSnapshot",
        "proposeForkGraphRefresh",
    }:
        errors.append("OPERATIONDINNER action set has drifted")

    guardrails = _mapping(manifest, "guardrails", errors)
    for key, expected in EXPECTED_GUARDRAILS.items():
        if guardrails.get(key) != expected:
            errors.append(f"guardrail {key!r} must equal {expected!r}")

    provenance = _mapping(manifest, "provenance", errors)
    if provenance.get("provider") != "GitHub REST API":
        errors.append("provenance provider must remain GitHub REST API")
    if provenance.get("observedAt") != manifest.get("observedAt"):
        errors.append("provenance timestamp must match the snapshot timestamp")
    if "parent.full_name" not in str(provenance.get("parentVerification", "")):
        errors.append("provenance must document direct-parent verification")

    if mission is not None:
        _validate_mission(mission, manifest, errors)
    if ontology is not None:
        _validate_ontology_binding(ontology, expected_binding, errors)
    return errors


def _validate_mission(mission: dict[str, Any], manifest: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(mission, dict):
        errors.append("mission root must be an object")
        return
    if mission.get("missionId") != "OPERATIONDINNER":
        errors.append("missionId must remain OPERATIONDINNER")
    if mission.get("target") != "BLACK_HOUSE_PUBLIC_DEFENSE_RESEARCH_ECOSYSTEM":
        errors.append("mission target has drifted")
    if mission.get("classification") != "public":
        errors.append("OPERATIONDINNER is restricted to public metadata")
    if mission.get("approvalState") != "COMPLETED":
        errors.append("mission must record its implemented state")
    if mission.get("mutation") is not False:
        errors.append("mission must not authorize external mutation")
    if set(mission.get("allowedTools", [])) != {
        "github_public_metadata_read",
        "local_manifest_validation",
    }:
        errors.append("mission allowedTools must remain read-only")
    result = mission.get("result", {})
    if result.get("externalExecutionPerformed") is not False:
        errors.append("mission must record that no external execution occurred")
    if result.get("repositoriesCreated") != 0 or result.get("repositoriesModified") != 0:
        errors.append("mission must not claim repository creation or modification")
    if result.get("sourceCodeExecuted") is not False:
        errors.append("mission must record that source code was not executed")
    count_map = {
        "verifiedForksRegistered": "verifiedSonoxoForkCount",
        "sourceOrganizationForksRegistered": "sourceOrganizationForkCount",
        "coverageGapsRecorded": "notPresentAsVerifiedSonoxoForkCount",
    }
    scope = manifest.get("scope", {})
    for result_key, scope_key in count_map.items():
        if result.get(result_key) != scope.get(scope_key):
            errors.append(f"mission result {result_key} does not match integration scope")
    metadata = mission.get("metadata", {})
    if metadata.get("officialityRule") != (
        "deptofdefense namespace is verified organization-hosted source; "
        "sonoxo namespace is an independent fork"
    ):
        errors.append("mission officiality rule must distinguish source and fork namespaces")
    if metadata.get("operationalAuthority") != "none":
        errors.append("mission must not claim operational authority")


def _validate_ontology_binding(
    ontology: dict[str, Any], binding: dict[str, Any], errors: list[str]
) -> None:
    if not isinstance(ontology, dict):
        errors.append("bound ontology root must be an object")
        return
    snapshot = ontology.get("sourceSnapshot", {})
    if snapshot.get("observedRepository", {}).get("fullName") != binding["repository"]:
        errors.append("bound ontology observed repository does not match integration")
    if snapshot.get("commit", {}).get("sha") != binding["forkHeadSha"]:
        errors.append("bound ontology commit does not match the pinned fork head")
    guardrails = ontology.get("guardrails", {})
    if guardrails.get("governmentAffiliationInferred") is not False:
        errors.append("bound ontology must not infer government affiliation")
    if guardrails.get("sourceCodeExecution") != "prohibited_by_ontology":
        errors.append("bound ontology must prohibit source-code execution")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    paths = [MANIFEST_PATH, MISSION_PATH, ONTOLOGY_PATH]
    if len(sys.argv) > 1:
        paths[0] = Path(sys.argv[1])
    try:
        manifest, mission, ontology = (_load(path) for path in paths)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read OPERATIONDINNER artifacts: {exc}")
        return 2

    errors = validate(manifest, mission, ontology)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "OK: OPERATIONDINNER registered 38 verified sonoxo forks, "
        "8 source-organization forks, and 25 coverage gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
