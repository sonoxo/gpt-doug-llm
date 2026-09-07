import copy
import json
from pathlib import Path

from tools.validate_operationdinner import validate

MANIFEST = Path("the-black-house/integrations/deptofdefense/operationdinner-fork-ecosystem.json")
MISSION = Path("the-black-house/missions/operationdinner.json")
ONTOLOGY = Path("foundry/ontology/llms-at-dod-ontology.json")


def load_artifacts():
    return tuple(
        json.loads(path.read_text(encoding="utf-8")) for path in (MANIFEST, MISSION, ONTOLOGY)
    )


def test_operationdinner_artifacts_are_valid():
    assert validate(*load_artifacts()) == []


def test_sonoxo_forks_cannot_be_labeled_official_dod():
    manifest, mission, ontology = load_artifacts()
    manifest["forkOwner"]["officialDoDStatus"] = True

    assert any(
        "never be labeled official DoD" in error for error in validate(manifest, mission, ontology)
    )


def test_direct_parent_must_remain_in_verified_source_namespace():
    manifest, mission, ontology = load_artifacts()
    manifest["verifiedSonoxoForks"][0]["directParent"] = "unverified/example"

    assert any(
        "must have a deptofdefense direct parent" in error
        for error in validate(manifest, mission, ontology)
    )


def test_fork_heads_must_be_commit_shas():
    manifest, mission, ontology = load_artifacts()
    manifest["verifiedSonoxoForks"][0]["forkHeadSha"] = "main"

    assert any(
        "invalid pinned head SHA" in error for error in validate(manifest, mission, ontology)
    )


def test_lineage_snapshot_is_cryptographically_pinned():
    manifest, mission, ontology = load_artifacts()
    manifest["verifiedSonoxoForks"][0]["forkHeadSha"] = "0" * 40

    assert any(
        "lineage snapshot digest" in error for error in validate(manifest, mission, ontology)
    )


def test_source_organization_upstream_lineage_is_pinned():
    manifest, mission, ontology = load_artifacts()
    manifest["sourceOrganizationForks"][0]["directParent"] = "deptofdefense/example"

    assert any(
        "incorrect upstream parent" in error for error in validate(manifest, mission, ontology)
    )


def test_coverage_counts_cannot_be_overstated():
    manifest, mission, ontology = load_artifacts()
    manifest["scope"]["verifiedSonoxoForkCount"] += 1

    assert any("pinned count" in error for error in validate(manifest, mission, ontology))


def test_actions_cannot_gain_network_egress():
    manifest, mission, ontology = load_artifacts()
    manifest["actions"][0]["networkEgress"] = True

    assert any("deny network egress" in error for error in validate(manifest, mission, ontology))


def test_mission_cannot_authorize_external_mutation():
    manifest, mission, ontology = load_artifacts()
    mission["mutation"] = True

    assert any(
        "must not authorize external mutation" in error
        for error in validate(manifest, mission, ontology)
    )


def test_ontology_commit_must_match_bound_fork_head():
    manifest, mission, ontology = load_artifacts()
    ontology = copy.deepcopy(ontology)
    ontology["sourceSnapshot"]["commit"]["sha"] = "0" * 40

    assert any("ontology commit" in error for error in validate(manifest, mission, ontology))
