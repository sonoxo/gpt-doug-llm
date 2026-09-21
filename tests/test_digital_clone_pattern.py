from gpt_chaos.digital_clone import evaluate_learning_event, pattern


def test_digital_clone_pattern_is_generalized_and_human_governed():
    data = pattern()
    assert data["source_patent"] == "US-20260279583-A1"
    assert data["mode"] == "GENERALIZED_NON_MEDICAL_ARCHITECTURE"
    assert data["policy"]["human_approval_for_major_actions"] is True
    assert data["policy"]["autonomous_medical_decisions"] is False
    assert data["policy"]["unrestricted_self_modification"] is False
    assert "EPISODIC_MEMORY_ARCHIVIST" in data["modules"]
    assert "META_LEARNING_PROPOSER" in data["modules"]
    assert data["body_mapping"]["LEARN"].startswith("archive")


def test_learning_event_blocks_secret_storage():
    result = evaluate_learning_event(
        has_provenance=True,
        contains_secret=True,
        is_sensitive_personal_data=False,
        user_consent=True,
        proposes_external_action=False,
        approved=False,
    )
    assert result["decision"] == "BLOCK"
    assert "SECRET_STORAGE_BLOCKED" in result["reasons"]


def test_learning_event_requires_consent_for_sensitive_data():
    result = evaluate_learning_event(
        has_provenance=True,
        contains_secret=False,
        is_sensitive_personal_data=True,
        user_consent=False,
        proposes_external_action=False,
        approved=False,
    )
    assert result["decision"] == "BLOCK"
    assert "CONSENT_REQUIRED_FOR_SENSITIVE_DATA" in result["reasons"]


def test_learning_event_allows_bounded_archival():
    result = evaluate_learning_event(
        has_provenance=True,
        contains_secret=False,
        is_sensitive_personal_data=False,
        user_consent=True,
        proposes_external_action=False,
        approved=False,
    )
    assert result["decision"] == "ALLOW"
    assert result["adaptation_mode"] == "PROPOSE_THEN_VALIDATE"
    assert result["self_modification"] == "DISABLED"
