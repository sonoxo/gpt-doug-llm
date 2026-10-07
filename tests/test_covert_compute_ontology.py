from __future__ import annotations

import json
from pathlib import Path

from tools.validate_covert_compute_ontology import validate

ONTOLOGY = Path("intel/supply-chain/covert-compute-c4ads-ontology.json")


def load_ontology() -> dict:
    return json.loads(ONTOLOGY.read_text(encoding="utf-8"))


def test_repository_ontology_is_valid():
    assert validate(load_ontology()) == []


def test_three_c4ads_pathways_are_preserved():
    data = load_ontology()
    pathways = {
        obj["id"]
        for obj in data["objects"]
        if obj["type"] == "AcquisitionPathway"
    }
    assert pathways == {
        "direct-university-research-acquisition",
        "southeast-asia-diversion-transshipment",
        "opaque-corporate-ownership",
    }


def test_public_report_aggregates_are_preserved():
    data = load_ontology()
    objects = {obj["id"]: obj for obj in data["objects"]}

    direct = objects["aggregate-direct-procurement"]["properties"]
    assert direct["count"] == 56
    assert direct["usdValue"] == 1_700_000
    assert direct["periodStart"] == "2025-07"
    assert direct["periodEnd"] == "2026-01"

    transit = objects["aggregate-transshipment"]["properties"]
    assert transit["count"] == 50
    assert transit["usdValue"] == 13_400_000
    assert transit["periodStart"] == "2023"
    assert transit["periodEnd"] == "2025"

    megaspeed = objects["aggregate-megaspeed-imports"]["properties"]
    assert megaspeed["usdValue"] == 4_600_000_000
    assert megaspeed["periodStart"] == "2022"
    assert megaspeed["periodEnd"] == "2025"


def test_transshipment_jurisdictions_match_source_summary():
    data = load_ontology()
    transit_links = {
        link["to"]
        for link in data["links"]
        if link["from"] == "southeast-asia-diversion-transshipment"
        and link["type"] == "PathwayRoutesThroughJurisdiction"
    }
    destinations = {
        link["to"]
        for link in data["links"]
        if link["from"] == "southeast-asia-diversion-transshipment"
        and link["type"] == "PathwayTargetsJurisdiction"
    }
    assert transit_links == {"vietnam", "india", "malaysia"}
    assert destinations == {"hong-kong", "china"}


def test_megaspeed_claim_keeps_attribution_and_no_owner_inference():
    data = load_ontology()
    objects = {obj["id"]: obj for obj in data["objects"]}
    characterization = objects["megaspeed-international-pte-ltd"]["properties"]["sourceCharacterization"]
    assert "C4ADS cites third-party reporting" in characterization
    assert data["guardrails"]["unnamedBeneficialOwnersInferred"] is False


def test_evasion_and_operational_assistance_are_fail_closed():
    guardrails = load_ontology()["guardrails"]
    assert guardrails["sanctionsEvasionAssistance"] is False
    assert guardrails["exportControlEvasionOptimization"] is False
    assert guardrails["restrictedChipSupplierSourcing"] is False
    assert guardrails["routingRecommendations"] is False
    assert guardrails["transshipmentOptimization"] is False
    assert guardrails["concealmentAdvice"] is False
    assert guardrails["falseEndUserDocumentation"] is False
    assert guardrails["automatedEnforcement"] is False
    assert guardrails["externalMutation"] is False
    assert guardrails["humanReviewRequired"] is True


def test_actions_are_read_only_and_review_gated():
    data = load_ontology()
    assert data["actions"]
    for action in data["actions"]:
        assert action["externalMutation"] is False
    review_actions = [a for a in data["actions"] if "requiresHumanReview" in a]
    assert review_actions
    assert all(a["requiresHumanReview"] is True for a in review_actions)
