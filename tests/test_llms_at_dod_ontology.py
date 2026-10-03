import copy
import json
from pathlib import Path

from tools.validate_llms_at_dod_ontology import validate

ONTOLOGY = Path("foundry/ontology/llms-at-dod-ontology.json")


def load_ontology():
    return json.loads(ONTOLOGY.read_text(encoding="utf-8"))


def test_repository_ontology_is_valid():
    assert validate(load_ontology()) == []


def test_fork_lineage_cannot_be_recast_as_official_fork_owner():
    data = load_ontology()
    data["sourceSnapshot"]["forkLineage"]["parent"] = "sonoxo/gpt-doug-llm"

    assert any("verified direct parent" in error for error in validate(data))


def test_source_digest_is_pinned():
    data = load_ontology()
    data["sourceSnapshot"]["evidenceArtifacts"][0]["sha256"] = "0" * 64

    assert any("field sha256" in error for error in validate(data))


def test_notebook_cell_provenance_must_be_in_range():
    data = load_ontology()
    record = next(item for item in data["evidence"] if item["evidenceId"] == "ev-rag-0")
    record["locator"]["cells"] = [32]

    assert any("out-of-range cell" in error for error in validate(data))


def test_links_cannot_have_dangling_endpoints():
    data = load_ontology()
    data["links"][0]["to"] = "missing-repository"

    assert any("dangling endpoint" in error for error in validate(data))


def test_actions_cannot_gain_network_egress():
    data = load_ontology()
    data["actions"][0]["networkEgress"] = True

    assert any("prohibit network egress" in error for error in validate(data))


def test_government_affiliation_guardrail_fails_closed():
    data = load_ontology()
    data["guardrails"]["governmentAffiliationInferred"] = True

    assert any("governmentAffiliationInferred" in error for error in validate(data))


def test_duplicate_object_ids_are_rejected():
    data = load_ontology()
    data["objects"].append(copy.deepcopy(data["objects"][0]))

    assert any("duplicate object id" in error for error in validate(data))
