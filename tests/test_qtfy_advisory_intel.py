import json
from pathlib import Path

from agents.adaptive_intelligence import AdaptiveIntel
from agents.qtfy_advisory_intel import (
    ADVISORY_ID,
    ATTACK_TECHNIQUES,
    ONTOLOGY_CONTRACT_PATH,
    advisory_evidence,
    build_qtfy_defensive_plan,
    ioc_action_policy,
)


def test_advisory_packet_is_grounded_and_absorbable():
    brain = AdaptiveIntel()
    items = advisory_evidence()
    assert len(items) >= 5
    assert brain.absorb(items) == len(items)
    packet = brain.ideate_packet("defend critical infrastructure from QTFY")
    assert packet["evidence"]
    assert any(ADVISORY_ID in item["source_id"] for item in packet["evidence"])


def test_attack_mapping_contains_advisory_techniques():
    assert set(ATTACK_TECHNIQUES) == {"T1595.002", "T1190", "T1505.003", "T1583.003", "T1587"}


def test_ioc_match_never_auto_blocks():
    policy = ioc_action_policy(indicator_match=True, corroborated=True)
    assert policy["action"] == "investigate-and-vet"
    assert policy["autoBlock"] is False
    assert policy["humanReviewRequired"] is True


def test_qtfy_plan_extends_critical_infrastructure_shield():
    plan = build_qtfy_defensive_plan()
    assert plan["advisoryId"] == ADVISORY_ID
    assert plan["mode"] == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
    assert plan["shield"]["severity"] == "CRITICAL"
    assert plan["iocPolicy"]["automaticBlocking"] is False
    lanes = {item["va3lm_lane"] for item in plan["controls"]}
    assert {
        "agent-inventory",
        "agent-identity",
        "agent-segmentation",
        "agent-detection",
        "agent-containment",
        "agent-recovery",
        "agent-verify",
    } <= lanes


def test_qtfy_plan_is_ontology_backed():
    plan = build_qtfy_defensive_plan()
    ontology = plan["ontology"]
    assert plan["ontologyContract"] == ONTOLOGY_CONTRACT_PATH
    assert {
        "CyberAdvisory",
        "ThreatProfile",
        "AttackTechnique",
        "IOCFeed",
        "Indicator",
        "Asset",
        "Detection",
        "Incident",
        "DefensiveControl",
        "DefensiveAction",
        "Evidence",
        "RecoveryValidation",
    } <= set(ontology["objectTypes"])
    assert ontology["guardrails"]["automaticBlocking"] is False
    assert ontology["guardrails"]["externalThirdPartyAction"] is False
    assert any(link["linkType"] == "AdvisoryProfilesThreat" for link in ontology["links"])
    assert any(action["apiName"] == "requestAuthorizedContainment" and action["requiresHumanReview"] for action in ontology["actions"])


def test_foundry_ontology_contract_matches_defensive_guardrails():
    contract = json.loads(Path(ONTOLOGY_CONTRACT_PATH).read_text(encoding="utf-8"))
    types = {item["apiName"] for item in contract["objectTypes"]}
    assert {"CyberAdvisory", "Indicator", "Asset", "Incident", "Evidence"} <= types
    assert contract["sourceAdvisory"] == ADVISORY_ID
    assert contract["guardrails"]["automaticBlocking"] is False
    assert contract["guardrails"]["humanApprovalForContainment"] is True
