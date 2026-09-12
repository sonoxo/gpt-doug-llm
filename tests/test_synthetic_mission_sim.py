import pytest

from agents.synthetic_mission_sim import (
    MODE,
    build_maven_simulation_event,
    normalize_scenario,
    run_simulation,
    sample_scenario,
    step_simulation,
)


def test_sample_scenario_is_simulation_only():
    state = normalize_scenario(sample_scenario())

    assert state["mode"] == MODE
    assert state["syntheticOnly"] is True
    assert state["operatorReviewRequired"] is True
    assert state["automaticExternalAction"] is False


def test_simulation_is_deterministic_and_replayable():
    first = run_simulation(sample_scenario(), ticks=6)
    second = run_simulation(sample_scenario(), ticks=6)

    assert first == second
    assert first["tick"] == 6
    assert len(first["history"]) == 6
    assert [item["tick"] for item in first["history"]] == [1, 2, 3, 4, 5, 6]


def test_simulation_requires_human_review_for_recommendations():
    state = run_simulation(sample_scenario(), ticks=6)
    assessment = state["assessment"]

    assert assessment["recommendedAction"] in {"OBSERVE", "SHIELD", "EVACUATE"}
    assert assessment["recommendationStatus"] == "PENDING_HUMAN_REVIEW"
    assert assessment["automaticExternalAction"] is False
    assert state["operatorReviewRequired"] is True


def test_step_changes_only_abstract_grid_state():
    state = normalize_scenario(sample_scenario())
    stepped = step_simulation(state)

    hazard = next(item for item in stepped["entities"] if item["entityId"] == "hazard-red-1")
    assert hazard["gridX"] == 11
    assert hazard["gridY"] == 4
    assert 0 <= hazard["gridX"] <= 19
    assert 0 <= hazard["gridY"] <= 19


@pytest.mark.parametrize(
    "field",
    [
        "latitude",
        "longitude",
        "coordinates",
        "weapon",
        "weapon_id",
        "munition",
        "aimpoint",
        "impact_point",
        "intercept_point",
        "guidance",
        "seeker",
        "fire_control",
        "target",
        "target_id",
        "person_id",
        "person_name",
        "biometric",
        "external_action",
        "actuation_command",
    ],
)
def test_restricted_fields_fail_closed(field):
    scenario = sample_scenario()
    scenario["entities"][0]["metadata"] = {field: "blocked"}

    with pytest.raises(ValueError, match="restricted field"):
        normalize_scenario(scenario)


def test_real_world_mode_cannot_be_enabled():
    scenario = sample_scenario()
    scenario["syntheticOnly"] = False

    with pytest.raises(ValueError, match="syntheticOnly must be true"):
        normalize_scenario(scenario)


def test_maven_event_remains_non_actuating():
    state = run_simulation(sample_scenario(), ticks=4)
    event = build_maven_simulation_event(state)

    assert event["objectType"] == "Scenario"
    assert event["properties"]["syntheticOnly"] is True
    assert event["properties"]["automaticExternalAction"] is False
    assert event["policy"]["humanReviewRequired"] is True
    assert event["policy"]["externalActuation"] is False
    assert event["policy"]["realWorldCoordinates"] is False
    assert event["policy"]["identityTracking"] is False


def test_tick_limit_is_bounded():
    with pytest.raises(ValueError, match="ticks must be between 1 and 100"):
        run_simulation(sample_scenario(), ticks=101)
