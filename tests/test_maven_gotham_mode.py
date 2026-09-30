from maven_gotham_mode import (
    ARTILLERY_MODE,
    GOTHAM_INVARIANTS,
    GOTHAM_PROFILE,
    INSTRUMENTATION_PROFILE,
    build_analytic_salvo,
    consequence_envelope,
    instrumentation_manifest,
    normalize_field_instrumentation,
)


def fixture_packet():
    return {
        "packetId": "packet-1",
        "domain": "CRITICAL_INFRASTRUCTURE",
        "reviewState": "PENDING_REVIEW",
        "track": {"entityRef": "critical-service-a", "latitude": 37.5, "longitude": -77.5},
        "assessment": {
            "severity": "HIGH",
            "confidence": 0.92,
            "recommendedActions": ["REQUEST_INSPECTION"],
        },
    }


def test_consequence_envelope_is_operational_not_targeting():
    envelope = consequence_envelope(fixture_packet())
    assert envelope.score > 0
    assert envelope.execution == "SIMULATION_ONLY"
    assert envelope.entity_ref == "critical-service-a"


def test_gotham_salvo_is_bounded_and_has_no_precise_coordinates():
    result = build_analytic_salvo([fixture_packet()])
    assert result["profile"] == GOTHAM_PROFILE
    assert result["mode"] == ARTILLERY_MODE
    assert result["human_review_required"] is True
    assert result["external_side_effects_executed"] is False
    assert len(result["analytic_rounds"]) == 1
    analytic_round = result["analytic_rounds"][0]
    assert "latitude" not in analytic_round
    assert "longitude" not in analytic_round


def test_safety_invariants_are_explicit():
    assert "NO_WEAPON_TARGET_SELECTION" in GOTHAM_INVARIANTS
    assert "NO_FIRE_CONTROL_OR_FIRING_SOLUTIONS" in GOTHAM_INVARIANTS
    assert "NO_KINETIC_STRIKE_EXECUTION" in GOTHAM_INVARIANTS
    assert "NO_PERSON_LEVEL_TARGET_RANKING" in GOTHAM_INVARIANTS



def test_safe_instrumentation_manifest_is_non_kinetic():
    manifest = instrumentation_manifest()
    assert manifest["profile"] == INSTRUMENTATION_PROFILE
    assert manifest["external_actuation"] is False
    assert "ballistic solution" in manifest["blocked_outputs"]
    assert "target designation" in manifest["blocked_outputs"]


def test_field_instrumentation_normalizes_benign_telemetry():
    packet = normalize_field_instrumentation(
        {
            "packet_id": "field-1",
            "sensor_id": "weather-node-a",
            "calibration_state": "green",
            "environment": {"temperature_c": 22.4, "wind_speed_mps": 3.1},
            "orientation": {"roll_deg": 0.2, "pitch_deg": 1.1},
            "platform_health": {"battery_pct": 88},
            "camera_state": {"status": "READY"},
            "provenance": {"source": "SIMULATED"},
        }
    )
    assert packet.calibration_state == "GREEN"
    assert packet.execution == "READ_ONLY_ANALYTICS"
    assert packet.environment["temperature_c"] == 22.4


def test_field_instrumentation_rejects_weapon_or_target_fields():
    try:
        normalize_field_instrumentation({"weapon": {"status": "ready"}})
    except ValueError as exc:
        assert "blocked instrumentation fields" in str(exc)
    else:
        raise AssertionError("weapon telemetry must be rejected")
