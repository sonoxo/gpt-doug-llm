import pytest

from agents.ballistic_warning import (
    BallisticWarningError,
    assess_warning,
    build_maven_ontology_event,
    normalize_simulated_track,
)


def base_track():
    return {
        "sourceMode": "SIMULATION_ONLY",
        "scenarioId": "exercise-001",
        "trackId": "synthetic-track-7",
        "observedAt": "2026-09-12T03:30:00-04:00",
        "classification": "BALLISTIC_LIKE",
        "zoneRelation": "NEAR",
        "confidence": 0.91,
        "trackQuality": 0.84,
        "sourceLabel": "tabletop-generator",
    }


def test_normalizes_simulation_track_without_geospatial_data():
    track = normalize_simulated_track(base_track())
    assert track["sourceMode"] == "SIMULATION_ONLY"
    assert track["classification"] == "BALLISTIC_LIKE"


def test_warning_requires_human_review_and_disables_engagement():
    assessment = assess_warning(base_track())
    assert assessment["severity"] == "WATCH"
    assert assessment["recommendedAction"] == "OPERATOR_REVIEW"
    assert assessment["humanAcknowledgementRequired"] is True
    assert assessment["automaticEngagement"] is False
    assert assessment["weaponsRelease"] is False
    assert assessment["fireControlCue"] is False
    assert assessment["interceptorRecommendation"] is False


def test_crossed_zone_can_raise_warning_but_not_weapon_action():
    observation = base_track()
    observation["zoneRelation"] = "CROSSED"
    assessment = assess_warning(observation)
    assert assessment["severity"] == "WARNING"
    assert assessment["recommendedAction"] == "OPERATOR_REVIEW"
    assert assessment["automaticEngagement"] is False


def test_rejects_live_source_mode():
    observation = base_track()
    observation["sourceMode"] = "LIVE_SENSOR"
    with pytest.raises(BallisticWarningError, match="SIMULATION_ONLY"):
        normalize_simulated_track(observation)


@pytest.mark.parametrize(
    "field",
    [
        "latitude",
        "longitude",
        "aimpoint",
        "impact_point",
        "launch_site",
        "intercept_point",
        "weapon_id",
        "guidance",
        "fire_control",
        "target_id",
    ],
)
def test_rejects_targeting_and_fire_control_fields(field):
    observation = base_track()
    observation[field] = "prohibited-value"
    with pytest.raises(BallisticWarningError, match="prohibited"):
        normalize_simulated_track(observation)


def test_maven_event_is_read_only_decision_support():
    assessment = assess_warning(base_track())
    event = build_maven_ontology_event(assessment)
    assert event["objectType"] == "BallisticWarningAssessment"
    assert event["policy"]["readOnlyDecisionSupport"] is True
    assert event["policy"]["humanReviewRequired"] is True
    assert event["policy"]["computesImpactPoint"] is False
    assert event["policy"]["computesLaunchOrigin"] is False
    assert event["policy"]["providesFireControlCue"] is False
    assert event["policy"]["recommendsInterceptor"] is False
