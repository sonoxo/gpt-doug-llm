from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SAFE_EMULATION_ENVIRONMENTS = {"synthetic", "isolated_lab", "owned_test"}
APPROVED_MUTATION_STATE = "APPROVED"


class ODScenario(BaseModel):
    scenarioId: str = Field(min_length=1)
    requestedBy: str = Field(default="black-house", min_length=1)
    mode: Literal["OFFENSE_EMULATION", "DEFENSE", "FULL_LOOP"] = "FULL_LOOP"
    environment: Literal[
        "synthetic", "isolated_lab", "owned_test", "production", "public_internet"
    ] = "synthetic"
    scope: list[str] = Field(default_factory=list)
    approvalState: str = "PENDING_POLICY"
    mutation: bool = False
    telemetry: list[dict[str, Any]] = Field(default_factory=list)


def od_plane_status() -> dict[str, Any]:
    return {
        "id": "BLACK_HOUSE_OD_PLANE_V1",
        "phase": 9,
        "state": "COMPLETE",
        "execution": "PLAN_OR_SIMULATION_ONLY",
        "controlLoop": [
            "SENSE",
            "TRANSPORT",
            "FUSE",
            "ASSESS",
            "EMULATE",
            "DEFEND",
            "VERIFY",
            "EVIDENCE",
        ],
        "offense": {
            "mode": "AUTHORIZED_LAB_EMULATION_ONLY",
            "allowedEnvironments": sorted(SAFE_EMULATION_ENVIRONMENTS),
            "liveExploitation": False,
        },
        "defense": {
            "mode": "DETECT_CONTAIN_RECOVER_VERIFY",
            "productionReadOnlyPlanning": True,
            "externalMutationRequiresApproval": True,
        },
        "safety": {
            "realWorldTargetsAllowed": False,
            "publicInternetExploitationAllowed": False,
            "criticalInfrastructureDisruptionAllowed": False,
            "weaponControlAllowed": False,
            "autonomousExternalMutationAllowed": False,
            "explicitScopeRequired": True,
            "unknownActionsFailClosed": True,
        },
    }


def _severity_score(telemetry: list[dict[str, Any]]) -> int:
    weights = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    score = 0
    for event in telemetry:
        severity = str(event.get("severity", "low")).lower()
        score += weights.get(severity, 1)
    return min(score, 100)


def _offense_emulation_plan() -> list[dict[str, str]]:
    return [
        {
            "stage": "EMULATE_IDENTITY_PRESSURE",
            "action": "Replay synthetic authentication anomalies inside the declared lab scope.",
        },
        {
            "stage": "EMULATE_MOVEMENT_SIGNAL",
            "action": "Inject synthetic graph edges representing suspicious east-west movement; do not open real sessions.",
        },
        {
            "stage": "EMULATE_DATA_ACCESS_ANOMALY",
            "action": "Generate synthetic access-spike telemetry against non-production fixtures.",
        },
    ]


def _defense_plan() -> list[dict[str, str]]:
    return [
        {
            "stage": "DETECT",
            "action": "Correlate endpoint, network, identity, cloud, application, and evidence signals.",
        },
        {
            "stage": "CONTAIN",
            "action": "Recommend isolation, deny-list, credential rotation, or workload quarantine for an authorized executor.",
        },
        {
            "stage": "RECOVER",
            "action": "Recommend restoration from known-good state and integrity checks before service return.",
        },
        {
            "stage": "VERIFY",
            "action": "Re-run telemetry checks, compare expected state, and attach evidence to the mission ledger.",
        },
    ]


def simulate_od_scenario(scenario: ODScenario) -> dict[str, Any]:
    if not scenario.scope:
        return {
            "status": "HOLD",
            "reason": "EXPLICIT_SCOPE_REQUIRED",
            "scenarioId": scenario.scenarioId,
        }

    requires_emulation = scenario.mode in {"OFFENSE_EMULATION", "FULL_LOOP"}
    if requires_emulation and scenario.environment not in SAFE_EMULATION_ENVIRONMENTS:
        return {
            "status": "HOLD",
            "reason": "EMULATION_REQUIRES_SYNTHETIC_OR_OWNED_LAB",
            "scenarioId": scenario.scenarioId,
            "environment": scenario.environment,
        }

    if scenario.mutation and scenario.approvalState != APPROVED_MUTATION_STATE:
        return {
            "status": "APPROVAL_REQUIRED",
            "reason": "MUTATION_REQUIRES_EXPLICIT_APPROVAL",
            "scenarioId": scenario.scenarioId,
        }

    offense = _offense_emulation_plan() if requires_emulation else []
    defense = _defense_plan() if scenario.mode in {"DEFENSE", "FULL_LOOP"} else []
    execution_mode = (
        "SIMULATION_ONLY"
        if scenario.environment in SAFE_EMULATION_ENVIRONMENTS
        else "READ_ONLY_DEFENSIVE_PLAN"
    )

    return {
        "status": "READY",
        "scenarioId": scenario.scenarioId,
        "requestedBy": scenario.requestedBy,
        "mode": scenario.mode,
        "environment": scenario.environment,
        "scope": scenario.scope,
        "riskScore": _severity_score(scenario.telemetry),
        "controlLoop": [
            "SENSE",
            "TRANSPORT",
            "FUSE",
            "ASSESS",
            "EMULATE" if requires_emulation else "SKIP_EMULATION",
            "DEFEND" if defense else "SKIP_DEFENSE",
            "VERIFY",
            "EVIDENCE",
        ],
        "offensePlan": offense,
        "defensePlan": defense,
        "executionMode": execution_mode,
        "externalExecutionPerformed": False,
        "evidence": {
            "telemetryEvents": len(scenario.telemetry),
            "provenance": "request-supplied-or-synthetic",
            "auditRequired": True,
        },
    }
