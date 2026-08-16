from pathlib import Path

from doug_core.heat_seek import (
    CIAStatus,
    Finding,
    calculate_cia,
    create_baseline,
    scan,
    turtle_environment,
    verify_audit_chain,
)


def test_cia_score():
    cia = CIAStatus(
        confidentiality=90,
        integrity=80,
        availability=100,
    )

    assert cia.overall == 90


def test_cia_deductions():

    findings = [
        Finding(
            control="C",
            severity="HIGH",
            title="test",
            detail="test",
            points=20,
        ),
        Finding(
            control="I",
            severity="MEDIUM",
            title="test",
            detail="test",
            points=10,
        ),
    ]

    cia = calculate_cia(
        findings
    )

    assert cia.confidentiality == 80
    assert cia.integrity == 90
    assert cia.availability == 100


def test_turtle_environment():
    env = turtle_environment(
        port=8788
    )

    assert (
        env["GPT_DOUG_PROVIDER"]
        == "none"
    )

    assert env["PORT"] == "8788"

    assert "OLLAMA_HOST" not in env


def test_baseline_creation():

    baseline = create_baseline()

    assert "files" in baseline
    assert baseline["files"]


def test_audit_chain():

    valid, message = (
        verify_audit_chain()
    )

    assert valid
    assert message


def test_full_scan():

    report = scan()

    assert (
        0
        <= report.cia.confidentiality
        <= 100
    )

    assert (
        0
        <= report.cia.integrity
        <= 100
    )

    assert (
        0
        <= report.cia.availability
        <= 100
    )

    assert (
        0
        <= report.cia.overall
        <= 100
    )
