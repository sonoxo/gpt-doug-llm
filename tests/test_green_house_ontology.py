from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "the-green-house" / "ontology" / "green-house-ontology.json"


def _load():
    return json.loads(ONTOLOGY.read_text())


def test_green_house_ontology_exists_and_is_scoped():
    data = _load()
    assert data["name"].startswith("The Green House")
    assert set(data["scope"]) == {"eco", "bio", "pharma", "fda"}
    assert data["deploymentState"] == "REPOSITORY_IMPLEMENTED"


def test_regulatory_truth_state_is_strict():
    data = _load()
    rules = data["truthStateRules"]
    assert "authoritative regulatory decision evidence" in rules["fdaApproved"]
    assert data["connectionState"] == "NO_EXTERNAL_REGULATOR_CONNECTION_CLAIMED"


def test_core_object_types_present():
    data = _load()
    ids = {item["id"] for item in data["objectTypes"]}
    required = {
        "greenhouse.Ecosystem",
        "greenhouse.Organism",
        "greenhouse.Biomaterial",
        "greenhouse.Compound",
        "greenhouse.DrugCandidate",
        "greenhouse.Study",
        "greenhouse.RegulatorySubmission",
        "greenhouse.RegulatoryDecision",
        "greenhouse.AdverseEvent",
        "greenhouse.SourceEvidence",
    }
    assert required <= ids


def test_no_approval_without_verification_action():
    data = _load()
    actions = {item["id"]: item for item in data["actionTypes"]}
    verify = actions["greenhouse.VERIFY_FDA_STATUS"]
    assert "authoritative_source_required" in verify["guardrails"]
    assert "approved_only_if_authoritative_decision_evidence" in verify["guardrails"]
