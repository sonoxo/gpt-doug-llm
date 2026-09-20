from gpt_chaos.aerospace import BlendedWingConcept, pattern, stress_test


def test_blended_wing_pattern_is_simulation_only():
    data = pattern()
    assert data["source_patent"] == "US-20260274413-A1"
    assert data["mode"] == "SIMULATION_ONLY"
    assert data["execution_boundary"] == "NO_REAL_WORLD_FLIGHT_OR_ACTUATION"
    assert "pusher" in data["trade_space"]["fan_architecture"]
    assert True in data["trade_space"]["boundary_layer_ingestion"]


def test_stress_test_adds_relevant_reviews():
    result = stress_test(
        BlendedWingConcept(
            engine_mount="trailing-edge-integrated",
            fan_architecture="pusher",
            boundary_layer_ingestion=True,
            variable_pitch_fan=True,
            engine_count=2,
        )
    )
    assert result["flight_release"] == "NOT_AUTHORIZED"
    assert "MODEL_INLET_DISTORTION_AND_PRESSURE_RECOVERY" in result["required_reviews"]
    assert "MODEL_ASYMMETRIC_PROPULSION_CASES" in result["required_reviews"]
