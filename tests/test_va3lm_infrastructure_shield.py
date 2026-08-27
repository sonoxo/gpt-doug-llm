import pytest

from agents.va3lm_infrastructure_shield import (
    PROHIBITED_ACTIONS,
    SHIELD_COMMAND,
    Severity,
    build_infrastructure_shield_plan,
    completion_evidence,
    normalize_severity,
    required_controls,
)


def test_high_severity_plan_is_defensive_and_federated():
    plan = build_infrastructure_shield_plan(severity="high")
    assert plan["command"] == SHIELD_COMMAND
    assert plan["mission"] == "PROTECT_US_DATA_AND_CRITICAL_INFRASTRUCTURE"
    assert plan["mode"] == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
    assert plan["severity"] == "HIGH"
    assert plan["federation"]["nationalKillSwitch"] is False
    assert plan["federation"]["localOperationalAuthority"] is True
    assert len(plan["lanes"]) == 7


def test_critical_incident_adds_continuity_controls():
    controls = required_controls(Severity.CRITICAL)
    assert "incident-command-activation" in controls
    assert "out-of-band-communications" in controls
    assert "continuity-of-operations-check" in controls


def test_completion_requires_every_evidence_gate():
    partial = completion_evidence(["critical-services-operational", "compromise-contained"])
    assert partial["complete"] is False
    assert "evidence-recorded" in partial["missing"]

    complete = completion_evidence(partial["required"])
    assert complete["complete"] is True
    assert complete["missing"] == []


def test_prohibited_actions_include_offensive_third_party_behavior():
    prohibited = " ".join(PROHIBITED_ACTIONS).lower()
    assert "unauthorized access" in prohibited
    assert "malware" in prohibited
    assert "denial-of-service" in prohibited
    assert "data exfiltration" in prohibited


def test_invalid_severity_is_rejected():
    with pytest.raises(ValueError):
        normalize_severity("maximum-overdrive")
