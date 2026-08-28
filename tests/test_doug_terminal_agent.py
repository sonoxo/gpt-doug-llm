import json

import doug_terminal_agent as agent


def test_finish_schema_exposes_verification_command():
    properties = agent.ACTION_SCHEMA["properties"]
    assert "verify_command" in properties
    assert properties["verify_command"]["type"] == "string"


def test_long_context_default_is_not_legacy_4k():
    assert agent.CONTEXT_WINDOW >= 262_144


def test_agent_horizon_is_configurable_and_extended():
    assert agent.MAX_STEPS >= 40


def test_finish_action_parses_verification_evidence():
    payload = {
        "action": "finish",
        "summary": "verified",
        "verify_command": "pytest -q",
    }
    assert agent.parse_action(json.dumps(payload)) == payload


def test_parse_action_rejects_non_object_json():
    try:
        agent.parse_action("[]")
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("non-object action should be rejected")
