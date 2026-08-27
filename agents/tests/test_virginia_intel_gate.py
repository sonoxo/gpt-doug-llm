from pathlib import Path

import pytest

from agents.virginia_intel_gate import VirginiaIntelGateError, doctrine_status, validate_intelligence

ROOT = Path(__file__).resolve().parents[2]


def _record(**overrides):
    value = {
        "sourceId": "DOJ-26-972",
        "sourceLocation": "intel/glassonion/DOJ-26-972.json",
        "intelligenceTier": 3,
        "intelligenceClass": "AGENCY_REPORTED_INTELLIGENCE",
        "provenanceLocator": "sourceLines:61-63",
        "jurisdiction": "FEDERAL",
        "statement": "A federal agency reported a court-authorized disruption action.",
        "impactFields": [],
    }
    value.update(overrides)
    return value


def test_doctrine_status_is_virginia_command():
    text = doctrine_status(ROOT)
    assert "VIRGINIA INTELLIGENCE COMMAND" in text
    assert "COMMAND REVIEW REQUIRED" in text


def test_valid_intelligence_clears_gate():
    result = validate_intelligence(ROOT, _record())
    assert result["status"] == "CLEARED"
    assert result["jurisdiction"] == "FEDERAL"


def test_allegation_cannot_be_marked_adjudicated():
    with pytest.raises(VirginiaIntelGateError):
        validate_intelligence(
            ROOT,
            _record(intelligenceClass="LEGAL_RECORD_ALLEGATION", adjudicated=True),
        )


def test_media_intelligence_cannot_directly_promote_fact():
    with pytest.raises(VirginiaIntelGateError):
        validate_intelligence(
            ROOT,
            _record(intelligenceTier=5, intelligenceClass="MEDIA_INTELLIGENCE_CLAIM", factPromotion=True),
        )


def test_high_impact_requires_command_review():
    with pytest.raises(VirginiaIntelGateError):
        validate_intelligence(
            ROOT,
            _record(impactFields=["attribution"]),
        )


def test_high_impact_can_clear_after_command_review():
    result = validate_intelligence(
        ROOT,
        _record(impactFields=["attribution"], commandReview="APPROVED"),
    )
    assert result["status"] == "CLEARED"
    assert result["commandReviewRequired"] is True
