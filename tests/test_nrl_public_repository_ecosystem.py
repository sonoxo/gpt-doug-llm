import copy
import json
from pathlib import Path

from tools.validate_nrl_public_repository_ecosystem import validate

MANIFEST = Path(
    "the-black-house/integrations/naval-research-laboratory/nrl-public-repository-ecosystem.json"
)
ONTOLOGY = Path("foundry/ontology/nrl-public-repository-ontology.json")
MISSION = Path("the-black-house/missions/operationdinner.json")


def load_artifacts():
    return tuple(
        json.loads(path.read_text(encoding="utf-8")) for path in (MANIFEST, ONTOLOGY, MISSION)
    )


def test_nrl_repository_ecosystem_is_valid():
    assert validate(*load_artifacts()) == []


def test_repository_snapshot_is_cryptographically_pinned():
    manifest, ontology, mission = load_artifacts()
    manifest["repositories"][0]["headSha"] = "0" * 40

    assert any("snapshot digest" in error for error in validate(manifest, ontology, mission))


def test_identity_cannot_be_promoted_to_uncited_github_verification():
    manifest, ontology, mission = load_artifacts()
    manifest["organization"]["identityState"] = "GITHUB_VERIFIED"

    assert any("identityState" in error for error in validate(manifest, ontology, mission))


def test_code_mil_upstream_lineage_is_preserved():
    manifest, ontology, mission = load_artifacts()
    fork = next(item for item in manifest["repositories"] if item["fork"])
    fork["directParent"] = "USNavalResearchLaboratory/code.mil"

    assert any("upstream lineage" in error for error in validate(manifest, ontology, mission))


def test_empty_repository_cannot_claim_a_commit():
    manifest, ontology, mission = load_artifacts()
    empty = next(
        item for item in manifest["repositories"] if item["headState"] == "EMPTY_REPOSITORY"
    )
    empty["headSha"] = "0" * 40

    assert any("must not claim a head" in error for error in validate(manifest, ontology, mission))


def test_repository_execution_guardrail_fails_closed():
    manifest, ontology, mission = load_artifacts()
    manifest["guardrails"]["repositoryContentExecution"] = True

    assert any(
        "repositoryContentExecution" in error for error in validate(manifest, ontology, mission)
    )


def test_metadata_descriptions_cannot_become_semantic_truth():
    manifest, ontology, mission = load_artifacts()
    ontology = copy.deepcopy(ontology)
    ontology["guardrails"]["semanticInferenceFromDescription"] = True

    assert any(
        "semanticInferenceFromDescription" in error
        for error in validate(manifest, ontology, mission)
    )


def test_mission_binding_remains_non_mutating():
    manifest, ontology, mission = load_artifacts()
    mission["mutation"] = True

    assert any(
        "public and non-mutating" in error for error in validate(manifest, ontology, mission)
    )
