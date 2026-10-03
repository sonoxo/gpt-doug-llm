from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PATENT_ID = "US-20260274413-A1"
PATTERN_ID = "BLENDED_WING_PUSHER_BLI_V1"


@dataclass(frozen=True)
class BlendedWingConcept:
    engine_mount: str = "aft-integrated"
    fan_architecture: str = "pusher"
    fan_enclosure: str = "nacelle"
    boundary_layer_ingestion: bool = True
    core_inlet_separate_from_fan_flow: bool = True
    inlet_channel_count: int = 1
    upstream_flow_conditioning: bool = True
    variable_pitch_fan: bool = True
    engine_count: int = 2


def pattern() -> dict[str, Any]:
    return {
        "pattern_id": PATTERN_ID,
        "source_patent": PATENT_ID,
        "mode": "SIMULATION_ONLY",
        "purpose": (
            "Explore independent blended-wing propulsion-airframe concepts using "
            "publicly described architecture signals from US-20260274413-A1."
        ),
        "default_concept": asdict(BlendedWingConcept()),
        "trade_space": {
            "engine_mount": [
                "aft-integrated",
                "trailing-edge-integrated",
                "top-pylon",
                "bottom-pylon",
                "aft-overhung",
            ],
            "fan_architecture": ["pusher", "tractor", "distributed-electric-comparison"],
            "fan_enclosure": ["nacelle", "open-rotor"],
            "boundary_layer_ingestion": [True, False],
            "core_inlet_separate_from_fan_flow": [True, False],
            "inlet_channel_count": [0, 1, 3],
            "upstream_flow_conditioning": [True, False],
            "variable_pitch_fan": [True, False],
            "engine_count": [1, 2, 3],
        },
        "metrics": [
            "pressure_recovery",
            "inlet_distortion",
            "boundary_layer_capture_fraction",
            "fan_efficiency",
            "net_propulsive_efficiency",
            "drag_delta",
            "installation_mass_penalty",
            "thermal_recirculation_risk",
            "acoustic_exposure",
            "foreign_object_susceptibility",
            "maintenance_accessibility",
            "asymmetric_propulsion_sensitivity",
        ],
        "chaos_scenarios": [
            "crosswind_inlet_distortion",
            "partial_boundary_layer_capture",
            "fan_pitch_actuator_degradation",
            "single_engine_performance_loss",
            "inlet_flow_separation",
            "thermal_recirculation",
            "sensor_bias_in_flow_estimation",
            "maintenance_access_penalty",
        ],
        "gates": [
            "PROVENANCE_REQUIRED",
            "CFD_OR_EQUIVALENT_AERO_REVIEW",
            "STRUCTURAL_AND_AEROELASTIC_REVIEW",
            "PROPULSION_FIRE_SAFETY_REVIEW",
            "STABILITY_AND_CONTROL_REVIEW",
            "HUMAN_ENGINEERING_RELEASE",
        ],
        "execution_boundary": "NO_REAL_WORLD_FLIGHT_OR_ACTUATION",
    }


def stress_test(concept: BlendedWingConcept | None = None) -> dict[str, Any]:
    chosen = concept or BlendedWingConcept()
    warnings: list[str] = []

    if chosen.boundary_layer_ingestion:
        warnings.append("MODEL_INLET_DISTORTION_AND_PRESSURE_RECOVERY")
    if chosen.fan_architecture == "pusher":
        warnings.append("MODEL_AFT_FLOW_INTERACTION_AND_THERMAL_RECIRCULATION")
    if chosen.engine_count > 1:
        warnings.append("MODEL_ASYMMETRIC_PROPULSION_CASES")
    if chosen.variable_pitch_fan:
        warnings.append("MODEL_PITCH_CONTROL_FAILURE_AND_REVERSE_THRUST_TRANSITIONS")
    if chosen.engine_mount in {"aft-integrated", "trailing-edge-integrated"}:
        warnings.append("MODEL_STRUCTURE_AEROELASTICITY_MAINTENANCE_AND_ACOUSTICS")

    return {
        "pattern_id": PATTERN_ID,
        "source_patent": PATENT_ID,
        "mode": "SIMULATION_ONLY",
        "concept": asdict(chosen),
        "required_reviews": warnings,
        "scenario_count": len(pattern()["chaos_scenarios"]),
        "flight_release": "NOT_AUTHORIZED",
    }
