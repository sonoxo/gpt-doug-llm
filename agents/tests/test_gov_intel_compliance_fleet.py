from pathlib import Path

from agents.gov_intel_compliance_fleet import audit, command_status, render_markdown


ROOT = Path(__file__).resolve().parents[2]


def test_fleet_has_no_repository_source_gaps():
    report = audit(ROOT)
    assert report["framework"] == "ZYRA GOVERNMENT INTELLIGENCE READINESS COMMAND"
    assert report["counts"]["subagents"] >= 8
    assert report["counts"]["sourceGaps"] == 0
    assert report["commandState"] == "SOURCE_READY_WITH_EXTERNAL_GATES"
    assert report["selfCertification"] is False


def test_external_authorization_is_not_self_declared():
    report = audit(ROOT)
    by_control = {item["control"]: item for item in report["findings"]}
    assert by_control["FEDRAMP_REV5_2026"]["state"] == "EXTERNAL_AUTHORIZATION_REQUIRED"
    assert by_control["FIPS_140_3"]["state"] == "EXTERNAL_OR_RUNTIME_EVIDENCE_REQUIRED"
    assert by_control["FBI_CJIS_SECURITY_POLICY_6_1"]["state"] == "EXTERNAL_OR_DEPLOYMENT_EVIDENCE_REQUIRED"
    assert by_control["NIST_SP_800_171_REV3"]["state"] == "EXTERNAL_OR_DEPLOYMENT_EVIDENCE_REQUIRED"


def test_security_gate_evidence_is_detected():
    report = audit(ROOT)
    by_control = {item["control"]: item for item in report["findings"]}
    nist = by_control["NIST_SP_800_53_REV5"]
    assert nist["state"] == "PARTIAL_EVIDENCE"
    assert ".github/workflows/security-gate.yml" in nist["evidence"]
    assert nist["gaps"] == []


def test_status_uses_command_language_and_exact_states():
    status = command_status(ROOT)
    assert "GOVERNMENT INTELLIGENCE READINESS" in status
    assert "SOURCE_READY_WITH_EXTERNAL_GATES" in status
    assert "FEDRAMP_REV5_2026: EXTERNAL_AUTHORIZATION_REQUIRED" in status


def test_markdown_refuses_generic_authorization_claim():
    text = render_markdown(audit(ROOT))
    assert "not FedRAMP authorization" in text
    assert "CJIS acceptance" in text
    assert "FIPS validation" in text
