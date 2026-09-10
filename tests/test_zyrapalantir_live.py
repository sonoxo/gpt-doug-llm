from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "zyrapalantir_live", ROOT / "scripts" / "zyrapalantir_live.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def finding(severity: str = "HIGH", description: str = "same finding") -> dict:
    return {
        "severity": severity,
        "category": "test",
        "target": "local-test-asset",
        "description": description,
        "recommendation": "review",
    }


def test_high_requires_three_consecutive_cycles_before_alert() -> None:
    f = finding("HIGH")
    state = {}

    state = MODULE.update_high_persistence(state, [f])
    needs_alert, _ = MODULE.alert_decision([f], state)
    assert needs_alert is False

    state = MODULE.update_high_persistence(state, [f])
    needs_alert, _ = MODULE.alert_decision([f], state)
    assert needs_alert is False

    state = MODULE.update_high_persistence(state, [f])
    needs_alert, reasons = MODULE.alert_decision([f], state)
    assert needs_alert is True
    assert "persisted 3 cycles" in reasons[0]


def test_high_persistence_resets_when_finding_disappears() -> None:
    f = finding("HIGH")
    state = MODULE.update_high_persistence({}, [f])
    state = MODULE.update_high_persistence(state, [])
    assert state == {}


def test_critical_alerts_immediately() -> None:
    f = finding("CRITICAL", "critical test condition")
    needs_alert, reasons = MODULE.alert_decision([f], {})
    assert needs_alert is True
    assert reasons[0].startswith("CRITICAL:")


def test_highest_severity() -> None:
    findings = [finding("LOW"), finding("MEDIUM"), finding("HIGH")]
    assert MODULE.highest_severity(findings) == "HIGH"


def test_live_ontology_prohibits_automatic_external_action() -> None:
    policy = MODULE.validate_live_policy()
    assert policy["mode"] == "DEFENSIVE_MONITORING_ONLY"
    assert policy["controls"]["automaticExternalAction"] is False
    assert policy["controls"]["artifactExecutionFromMonitor"] is False
