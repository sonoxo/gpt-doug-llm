from agents.adaptive_intelligence import AdaptiveIntel
from agents.qtfy_advisory_intel import (
    ADVISORY_ID,
    ATTACK_TECHNIQUES,
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
