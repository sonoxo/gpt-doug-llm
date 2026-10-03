"""Deterministic synthetic mission simulation for ZYRA / XUNIA.

This module models abstract entities on a bounded integer grid for training,
replay, analyst review, and ontology integration. It intentionally excludes
real-world coordinates, weapon parameters, identity tracking, and external
actuation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

MODE = "SYNTHETIC_MISSION_SIMULATION"
GRID_MIN = 0
GRID_MAX = 19
ALLOWED_TEAMS = {"ALLY", "OPPOSING", "NEUTRAL"}
ALLOWED_KINDS = {"SENSOR", "MOBILE_ASSET", "HAZARD", "PROTECTED_ZONE"}
ALLOWED_RECOMMENDATIONS = {"OBSERVE", "REPOSITION", "SHIELD", "EVACUATE", "HOLD"}

FORBIDDEN_FIELDS = {
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
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
}


def _scan_forbidden(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_FIELDS:
                raise ValueError(f"restricted field is not permitted: {path}.{key}")
            _scan_forbidden(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _scan_forbidden(nested, f"{path}[{index}]")


def _grid_value(value: Any, field: str) -> int:
    number = int(value)
    if not GRID_MIN <= number <= GRID_MAX:
        raise ValueError(f"{field} must be between {GRID_MIN} and {GRID_MAX}")
    return number


def _unit_interval(value: Any, field: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return number


def _normalize_entity(item: Mapping[str, Any]) -> dict[str, Any]:
    _scan_forbidden(item)
    entity_id = str(item.get("entityId", "")).strip()
    if not entity_id:
        raise ValueError("entityId is required")

    team = str(item.get("team", "NEUTRAL")).upper()
    kind = str(item.get("kind", "MOBILE_ASSET")).upper()
    if team not in ALLOWED_TEAMS:
        raise ValueError(f"team must be one of {sorted(ALLOWED_TEAMS)}")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"kind must be one of {sorted(ALLOWED_KINDS)}")

    entity = {
        "entityId": entity_id,
        "team": team,
        "kind": kind,
        "gridX": _grid_value(item.get("gridX", 0), "gridX"),
        "gridY": _grid_value(item.get("gridY", 0), "gridY"),
        "stepX": max(-1, min(1, int(item.get("stepX", 0)))),
        "stepY": max(-1, min(1, int(item.get("stepY", 0)))),
        "confidence": _unit_interval(item.get("confidence", 1.0), "confidence"),
        "quality": _unit_interval(item.get("quality", 1.0), "quality"),
        "metadata": deepcopy(dict(item.get("metadata", {}))),
    }
    _scan_forbidden(entity)
    return entity


def normalize_scenario(scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a simulation-only scenario."""

    if not isinstance(scenario, Mapping):
        raise TypeError("scenario must be a mapping")
    _scan_forbidden(scenario)

    scenario_id = str(scenario.get("scenarioId", "")).strip()
    if not scenario_id:
        raise ValueError("scenarioId is required")
    if scenario.get("syntheticOnly") is not True:
        raise ValueError("syntheticOnly must be true")

    entities = [_normalize_entity(item) for item in scenario.get("entities", [])]
    if not entities:
        raise ValueError("at least one synthetic entity is required")

    entity_ids = [item["entityId"] for item in entities]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("entityId values must be unique")

    return {
        "mode": MODE,
        "scenarioId": scenario_id,
        "syntheticOnly": True,
        "tick": 0,
        "entities": entities,
        "history": [],
        "operatorReviewRequired": True,
        "automaticExternalAction": False,
    }


def _distance(a: Mapping[str, Any], b: Mapping[str, Any]) -> int:
    """Return abstract Manhattan grid distance in cells."""

    return abs(int(a["gridX"]) - int(b["gridX"])) + abs(int(a["gridY"]) - int(b["gridY"]))


def _move(entity: Mapping[str, Any]) -> dict[str, Any]:
    moved = deepcopy(dict(entity))
    if moved["kind"] not in {"MOBILE_ASSET", "HAZARD"}:
        return moved
    moved["gridX"] = max(GRID_MIN, min(GRID_MAX, moved["gridX"] + moved["stepX"]))
    moved["gridY"] = max(GRID_MIN, min(GRID_MAX, moved["gridY"] + moved["stepY"]))
    return moved


def _assess_state(entities: list[Mapping[str, Any]]) -> dict[str, Any]:
    protected = [item for item in entities if item["kind"] == "PROTECTED_ZONE"]
    hazards = [item for item in entities if item["kind"] == "HAZARD"]
    sensors = [item for item in entities if item["kind"] == "SENSOR"]

    closest = None
    for zone in protected:
        for hazard in hazards:
            distance = _distance(zone, hazard)
            candidate = {
                "protectedEntityId": zone["entityId"],
                "hazardEntityId": hazard["entityId"],
                "distanceCells": distance,
            }
            if closest is None or distance < closest["distanceCells"]:
                closest = candidate

    if closest is None:
        recommendation = "OBSERVE"
        alert_level = "INFO"
    elif closest["distanceCells"] <= 2:
        recommendation = "EVACUATE"
        alert_level = "HIGH"
    elif closest["distanceCells"] <= 5:
        recommendation = "SHIELD"
        alert_level = "MEDIUM"
    else:
        recommendation = "OBSERVE"
        alert_level = "LOW"

    if recommendation not in ALLOWED_RECOMMENDATIONS:
        raise RuntimeError("invalid simulation recommendation")

    sensor_quality = (
        sum(float(item["confidence"]) * float(item["quality"]) for item in sensors) / len(sensors)
        if sensors
        else 0.0
    )
    safety_score = 100
    if closest is not None:
        safety_score -= max(0, 30 - (closest["distanceCells"] * 5))
    safety_score = max(0, min(100, safety_score))

    return {
        "alertLevel": alert_level,
        "closestHazard": closest,
        "recommendedAction": recommendation,
        "recommendationStatus": "PENDING_HUMAN_REVIEW",
        "sensorQuality": round(sensor_quality, 4),
        "safetyScore": safety_score,
        "automaticExternalAction": False,
    }


def step_simulation(state: Mapping[str, Any]) -> dict[str, Any]:
    """Advance one deterministic synthetic tick and append replay state."""

    _scan_forbidden(state)
    if state.get("mode") != MODE or state.get("syntheticOnly") is not True:
        raise ValueError("state must be a normalized synthetic mission simulation")

    next_state = deepcopy(dict(state))
    next_state["tick"] = int(state.get("tick", 0)) + 1
    next_state["entities"] = [_move(item) for item in state["entities"]]
    assessment = _assess_state(next_state["entities"])
    snapshot = {
        "tick": next_state["tick"],
        "entities": deepcopy(next_state["entities"]),
        "assessment": assessment,
    }
    next_state["history"] = [*deepcopy(list(state.get("history", []))), snapshot]
    next_state["assessment"] = assessment
    next_state["operatorReviewRequired"] = True
    next_state["automaticExternalAction"] = False
    return next_state


def run_simulation(scenario: Mapping[str, Any], ticks: int = 6) -> dict[str, Any]:
    """Run a bounded deterministic replay for analyst training."""

    if not 1 <= int(ticks) <= 100:
        raise ValueError("ticks must be between 1 and 100")
    state = normalize_scenario(scenario)
    for _ in range(int(ticks)):
        state = step_simulation(state)
    return state


def build_maven_simulation_event(state: Mapping[str, Any]) -> dict[str, Any]:
    """Produce a Maven/Foundry-friendly summary event with no actuation path."""

    _scan_forbidden(state)
    if state.get("mode") != MODE:
        raise ValueError(f"state mode must be {MODE}")
    assessment = dict(state.get("assessment", {}))
    return {
        "objectType": "Scenario",
        "objectId": f"simulation:{state['scenarioId']}",
        "properties": {
            "scenarioId": state["scenarioId"],
            "mode": MODE,
            "tick": state["tick"],
            "alertLevel": assessment.get("alertLevel", "INFO"),
            "recommendedAction": assessment.get("recommendedAction", "OBSERVE"),
            "reviewStatus": assessment.get("recommendationStatus", "PENDING_HUMAN_REVIEW"),
            "safetyScore": assessment.get("safetyScore", 100),
            "syntheticOnly": True,
            "automaticExternalAction": False,
        },
        "policy": {
            "syntheticOnly": True,
            "humanReviewRequired": True,
            "externalActuation": False,
            "realWorldCoordinates": False,
            "identityTracking": False,
        },
    }


def sample_scenario() -> dict[str, Any]:
    """Return a deterministic abstract demo fixture."""

    return {
        "scenarioId": "mss-sim-demo-001",
        "syntheticOnly": True,
        "entities": [
            {
                "entityId": "protected-alpha",
                "team": "ALLY",
                "kind": "PROTECTED_ZONE",
                "gridX": 4,
                "gridY": 4,
            },
            {
                "entityId": "sensor-alpha",
                "team": "ALLY",
                "kind": "SENSOR",
                "gridX": 5,
                "gridY": 5,
                "confidence": 0.95,
                "quality": 0.9,
            },
            {
                "entityId": "hazard-red-1",
                "team": "OPPOSING",
                "kind": "HAZARD",
                "gridX": 12,
                "gridY": 4,
                "stepX": -1,
                "stepY": 0,
                "confidence": 0.85,
                "quality": 0.8,
            },
        ],
    }
