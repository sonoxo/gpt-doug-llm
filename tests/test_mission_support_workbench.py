import pytest

from agents.mission_support_workbench import (
    MODE,
    build_maven_event,
    correlate_case,
    normalize_evidence,
    workbench_manifest,
)


def _item(**overrides):
    item = {
        "evidenceId": "evidence-1",
        "caseId": "case-001",
        "observedAt": "2026-09-12T08:00:00Z",
        "source": "authorized-demo-source",
        "category": "availability",
        "severity": "MEDIUM",
        "confidence": 0.9,
        "quality": 0.8,
        "summary": "Synthetic mission-support evidence.",
        "metadata": {"demo": True},
    }
    item.update(overrides)
    return item


def test_normalize_evidence_preserves_provenance_fields():
    normalized = normalize_evidence(_item())

    assert normalized["caseId"] == "case-001"
    assert normalized["source"] == "authorized-demo-source"
    assert normalized["confidence"] == 0.9
    assert normalized["quality"] == 0.8
    assert normalized["observedAt"].endswith("Z")


def test_case_correlation_requires_one_case():
    with pytest.raises(ValueError, match="share caseId"):
        correlate_case([_item(), _item(evidenceId="evidence-2", caseId="case-002")])


def test_case_correlation_is_human_review_only():
    packet = correlate_case(
        [
            _item(),
            _item(
                evidenceId="evidence-2",
                observedAt="2026-09-12T08:05:00Z",
                source="authorized-demo-source-2",
                confidence=0.8,
                quality=0.9,
                severity="HIGH",
            ),
        ]
    )

    assert packet["mode"] == MODE
    assert packet["reviewStatus"] == "PENDING_HUMAN_REVIEW"
    assert packet["recommendedAction"] == "REVIEW_EVIDENCE"
    assert packet["automaticExternalAction"] is False
    assert packet["sourceCount"] == 2
    assert packet["highestSeverity"] == "HIGH"
    assert 0.0 <= packet["reviewPriority"] <= 1.0


def test_maven_event_is_read_only_decision_support():
    packet = correlate_case([_item()])
    event = build_maven_event(packet)

    assert event["objectType"] == "DecisionPacket"
    assert event["policy"]["mode"] == MODE
    assert event["policy"]["humanReviewRequired"] is True
    assert event["policy"]["readOnlyDecisionSupport"] is True
    assert event["policy"]["externalActuation"] is False
    assert event["properties"]["automaticExternalAction"] is False


@pytest.mark.parametrize(
    "field",
    [
        "person_id",
        "person_name",
        "biometric",
        "face_id",
        "phone_number",
        "external_action",
        "actuation_command",
    ],
)
def test_restricted_fields_fail_closed(field):
    with pytest.raises(ValueError, match="restricted field"):
        normalize_evidence(_item(metadata={field: "blocked"}))


def test_manifest_keeps_execution_boundary_explicit():
    manifest = workbench_manifest()

    assert manifest["mode"] == MODE
    assert manifest["controls"]["humanReviewRequired"] is True
    assert manifest["controls"]["externalActuation"] is False
    assert manifest["controls"]["identityTracking"] is False
    assert manifest["controls"]["provenanceRequired"] is True
