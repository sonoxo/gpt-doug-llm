import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "the-black-house/policy-signals/2026-09-14-us-ai-guardrails.json"
README = ROOT / "the-black-house/policy-signals/README.md"


def test_ai_guardrails_public_statement_keeps_authority_boundaries():
    data = json.loads(SIGNAL.read_text(encoding="utf-8"))

    assert data["controlPlane"] == "THE_BLACK_HOUSE_V1"
    assert data["signalType"] == "PUBLIC_STATEMENT"
    assert data["actor"]["role"] == "President of the United States"
    assert data["topics"] == [
        "AI_REGULATION",
        "DATA_CENTERS",
        "US_CHINA_AI_COMPETITION",
    ]
    assert data["stance"]["aiGuardrails"] == "OPPOSES_ADDITIONAL_GUARDRAILS"
    assert data["legalEffect"] == "NONE_BY_ITSELF"
    assert data["authorityEffect"]["changesBlackHouseExecutionAuthority"] is False
    assert data["authorityEffect"]["changesZyraApprovalRequirements"] is False
    assert data["authorityEffect"]["grantsExternalAuthorization"] is False


def test_ai_guardrails_signal_preserves_source_uncertainty_and_provenance():
    data = json.loads(SIGNAL.read_text(encoding="utf-8"))

    assert data["source"]["sourceType"] == "USER_SUPPLIED_SCREENSHOT"
    assert data["source"]["observedOn"] == "2026-09-14"
    assert data["source"]["statementDateVerified"] is False
    assert data["source"]["statementDate"] is None
    assert data["provenance"]["speakerClaimsAreNotIndependentFacts"] is True
    assert data["provenance"]["enactedPolicyMustBeVerifiedSeparately"] is True


def test_policy_signal_readme_requires_typed_authority_and_zyra_boundary():
    text = README.read_text(encoding="utf-8")

    for marker in (
        "PUBLIC_STATEMENT",
        "EXECUTIVE_ORDER",
        "LAW",
        "REGULATION",
        "does not change Black House execution authority",
        "ZYRA",
        "provenance",
    ):
        assert marker in text
