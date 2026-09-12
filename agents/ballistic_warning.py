"""Simulation-only ballistic warning decision support for ZYRA / Maven.

This module intentionally does not calculate trajectories, impact points, launch
origins, interceptor solutions, fire-control cues, or weapons-release actions.
It consumes abstract synthetic scenario observations and emits human-reviewed
warning assessments suitable for ontology ingestion and audit workflows.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

MODE = "SIMULATION_ONLY"
ALLOWED_CLASSIFICATIONS = {"BENIGN", "UNKNOWN", "BALLISTIC_LIKE"}
ALLOWED_ZONE_RELATIONS = {"OUTSIDE", "NEAR", "CROSSED", "UNKNOWN"}

# Reject fields that could turn this warning-only component into a targeting,
# fire-control, or real-world geospatial system.
FORBIDDEN_KEYS = frozenset(
    {
        "lat",
        "latitude",
        "lon",
        "lng",
        "longitude",
        "coordinates",
        "ecef",
        "eci",
        "aimpoint",
        "impactpoint",
        "impact_point",
        "predictedimpact",
        "predicted_impact",
        "launchsite",
        "launch_site",
        "intercept",
        "interceptpoint",
        "intercept_point",
        "intercepttime",
        "intercept_time",
        "weapon",
        "weaponid",
        "weapon_id",
        "guidance",
        "seeker",
        "firecontrol",
        "fire_control",
        "target",
        "targetid",
        "target_id",
    }
)


class BallisticWarningError(ValueError):
    """Raised when an observation violates the simulation-only contract."""


def _normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "")


def _assert_no_forbidden_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = _normalized_key(key)
            if normalized in FORBIDDEN_KEYS:
                raise BallisticWarningError(
                    f"field '{path}.{key}' is prohibited in simulation-only warning mode"
                )
            _assert_no_forbidden_fields(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_no_forbidden_fields(nested, f"{path}[{index}]")


def _unit_interval(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BallisticWarningError(f"{field} must be numeric") from exc
    if not 0.0 <= number <= 1.0:
        raise BallisticWarningError(f"{field} must be between 0 and 1")
    return number


def normalize_simulated_track(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one abstract synthetic track observation."""
    if not isinstance(observation, Mapping):
        raise BallisticWarningError("observation must be a mapping")
    _assert_no_forbidden_fields(observation)

    source_mode = str(observation.get("sourceMode", "")).strip().upper()
    if source_mode != MODE:
        raise BallisticWarningError("sourceMode must be SIMULATION_ONLY")

    scenario_id = str(observation.get("scenarioId", "")).strip()
    track_id = str(observation.get("trackId", "")).strip()
    if not scenario_id:
        raise BallisticWarningError("scenarioId is required")
    if not track_id:
        raise BallisticWarningError("trackId is required")

    classification = str(observation.get("classification", "UNKNOWN")).strip().upper()
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise BallisticWarningError("unsupported classification")

    zone_relation = str(observation.get("zoneRelation", "UNKNOWN")).strip().upper()
    if zone_relation not in ALLOWED_ZONE_RELATIONS:
        raise BallisticWarningError("unsupported zoneRelation")

    confidence = _unit_interval(observation.get("confidence", 0.0), "confidence")
    track_quality = _unit_interval(observation.get("trackQuality", 0.0), "trackQuality")

    return {
        "sourceMode": MODE,
        "scenarioId": scenario_id,
        "trackId": track_id,
        "observedAt": observation.get("observedAt"),
        "classification": classification,
        "zoneRelation": zone_relation,
        "confidence": confidence,
        "trackQuality": track_quality,
        "sourceLabel": str(observation.get("sourceLabel", "synthetic-scenario")),
    }


def assess_warning(track: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a normalized synthetic track into an operator warning assessment."""
    normalized = normalize_simulated_track(track)
    classification = normalized["classification"]
    relation = normalized["zoneRelation"]
    confidence = normalized["confidence"]
    quality = normalized["trackQuality"]

    severity = "NOTICE"
    rationale = "Synthetic track does not meet warning threshold."

    if classification == "BALLISTIC_LIKE" and confidence >= 0.8 and quality >= 0.6:
        if relation == "CROSSED":
            severity = "WARNING"
            rationale = "High-confidence synthetic ballistic-like track crossed the abstract scenario zone."
        elif relation == "NEAR":
            severity = "WATCH"
            rationale = "High-confidence synthetic ballistic-like track is near the abstract scenario zone."
        else:
            severity = "WATCH"
            rationale = "High-confidence synthetic ballistic-like pattern requires operator review."
    elif classification in {"BALLISTIC_LIKE", "UNKNOWN"} and confidence >= 0.5:
        severity = "WATCH"
        rationale = "Synthetic track is uncertain or incomplete and requires operator review."

    return {
        "mode": MODE,
        "scenarioId": normalized["scenarioId"],
        "trackId": normalized["trackId"],
        "severity": severity,
        "rationale": rationale,
        "classification": classification,
        "confidence": confidence,
        "trackQuality": quality,
        "zoneRelation": relation,
        "recommendedAction": "OPERATOR_REVIEW",
        "humanAcknowledgementRequired": True,
        "automaticEngagement": False,
        "weaponsRelease": False,
        "fireControlCue": False,
        "interceptorRecommendation": False,
    }


def build_maven_ontology_event(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Create a guarded ontology payload for the Maven/Foundry integration layer."""
    _assert_no_forbidden_fields(assessment)
    if assessment.get("mode") != MODE:
        raise BallisticWarningError("assessment mode must be SIMULATION_ONLY")

    return {
        "objectType": "BallisticWarningAssessment",
        "objectId": f"warning:{assessment.get('scenarioId')}:{assessment.get('trackId')}",
        "properties": dict(assessment),
        "links": [
            {
                "linkType": "AssessmentBelongsToScenario",
                "to": f"BallisticWarningScenario:{assessment.get('scenarioId')}",
            }
        ],
        "policy": {
            "mode": MODE,
            "readOnlyDecisionSupport": True,
            "humanReviewRequired": True,
            "automaticEngagement": False,
            "weaponsRelease": False,
            "computesImpactPoint": False,
            "computesLaunchOrigin": False,
            "providesFireControlCue": False,
            "recommendsInterceptor": False,
        },
    }


def evaluate_simulation(observations: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate synthetic observations and return Maven-ready ontology events."""
    events: list[dict[str, Any]] = []
    for observation in observations:
        assessment = assess_warning(observation)
        events.append(build_maven_ontology_event(assessment))
    return events
