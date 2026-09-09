from datetime import datetime, timedelta, timezone

import pytest

from flipper_ontology import (
    ActionType,
    AssetAuthorization,
    AuthorizationState,
    FlipperOntology,
)


def build_authorized_runtime():
    ontology = FlipperOntology()
    ontology.register_device(
        "flipper-001",
        "doug",
        firmware="test",
        authorization_state=AuthorizationState.OWNER_AUTHORIZED,
    )
    ontology.register_asset(
        "lab-remote-001",
        "Owned Lab Remote",
        "doug",
        authorization_status=AssetAuthorization.OWNED,
    )
    auth = ontology.grant_authorization(
        "doug",
        "flipper-001",
        "lab-remote-001",
        [
            "SESSION",
            ActionType.OBSERVE_SIGNAL.value,
            ActionType.CREATE_DIGITAL_TWIN.value,
            ActionType.RUN_SIMULATION.value,
            ActionType.EXECUTE_AUTHORIZED_TEST.value,
        ],
        evidence_reference="tests/fixture-owner-authorization",
    )
    return ontology, auth


def test_authorized_observe_to_digital_twin_simulation_flow():
    ontology, auth = build_authorized_runtime()
    session = ontology.start_session(
        "doug",
        "flipper-001",
        "lab-remote-001",
        auth["authorization_id"],
        "Owned-device protocol lab",
    )
    observation = ontology.observe_signal(
        session["session_id"],
        "infrared",
        "NEC",
        {"sample": "metadata-only"},
    )
    twin = ontology.create_digital_twin(
        session["session_id"],
        "NEC",
        {"power": "off"},
        [observation["observation_id"]],
    )
    result = ontology.request_action(
        session["session_id"],
        ActionType.RUN_SIMULATION,
        twin_id=twin["twin_id"],
        parameters={"simulated_transition": "power_on"},
    )

    assert result["decision"] == "ALLOWED"
    assert result["execution"] == "SIMULATION_ONLY"
    assert ontology.summary()["object_counts"]["DigitalTwin"] == 1


def test_unknown_asset_is_denied_by_default():
    ontology = FlipperOntology()
    ontology.register_device("flipper-001", "doug")
    ontology.register_asset(
        "unknown-001",
        "Unknown Device",
        "unknown",
        authorization_status=AssetAuthorization.UNKNOWN,
    )
    auth = ontology.grant_authorization(
        "doug",
        "flipper-001",
        "unknown-001",
        ["SESSION"],
    )

    with pytest.raises(PermissionError, match="asset is not authorized"):
        ontology.start_session(
            "doug",
            "flipper-001",
            "unknown-001",
            auth["authorization_id"],
            "must fail",
        )


def test_protected_real_world_asset_class_is_blocked():
    ontology = FlipperOntology()
    ontology.register_device("flipper-001", "doug")
    ontology.register_asset(
        "utility-001",
        "Synthetic Name But Classified Real Utility",
        "doug",
        authorization_status=AssetAuthorization.OWNED,
        protected_class="UTILITY_INFRASTRUCTURE",
    )
    auth = ontology.grant_authorization(
        "doug",
        "flipper-001",
        "utility-001",
        ["SESSION"],
    )

    with pytest.raises(PermissionError, match="protected real-world asset class is blocked"):
        ontology.start_session(
            "doug",
            "flipper-001",
            "utility-001",
            auth["authorization_id"],
            "must fail",
        )


def test_expired_authorization_cannot_start_session():
    ontology = FlipperOntology()
    ontology.register_device("flipper-001", "doug")
    ontology.register_asset(
        "lab-001",
        "Owned Lab Device",
        "doug",
        authorization_status=AssetAuthorization.OWNED,
    )
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    auth = ontology.grant_authorization(
        "doug",
        "flipper-001",
        "lab-001",
        ["SESSION"],
        expires_at=expired,
    )

    with pytest.raises(PermissionError, match="authorization does not permit a session"):
        ontology.start_session(
            "doug",
            "flipper-001",
            "lab-001",
            auth["authorization_id"],
            "expired auth",
        )


def test_physical_test_is_staged_and_never_actuated_by_ontology_runtime():
    ontology, auth = build_authorized_runtime()
    session = ontology.start_session(
        "doug",
        "flipper-001",
        "lab-remote-001",
        auth["authorization_id"],
        "Owned-device authorized test request",
    )
    result = ontology.request_action(
        session["session_id"],
        ActionType.EXECUTE_AUTHORIZED_TEST,
        parameters={"adapter": "not-attached"},
    )

    assert result["decision"] == "STAGED"
    assert result["execution"] == "NO_PHYSICAL_ACTUATION"
    assert result["human_review_required"] is True
