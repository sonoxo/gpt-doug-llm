from fastapi.testclient import TestClient

from va3lm.app import app
from va3lm.od_plane import ODScenario, simulate_od_scenario


def test_full_loop_runs_only_as_lab_simulation():
    result = simulate_od_scenario(
        ODScenario(
            scenarioId="phase9-lab",
            requestedBy="pytest",
            mode="FULL_LOOP",
            environment="isolated_lab",
            scope=["lab-segment-a"],
            telemetry=[{"signal": "auth-anomaly", "severity": "high"}],
        )
    )
    assert result["status"] == "READY"
    assert result["executionMode"] == "SIMULATION_ONLY"
    assert result["externalExecutionPerformed"] is False
    assert result["offensePlan"]
    assert result["defensePlan"]


def test_offense_emulation_fails_closed_on_public_internet():
    result = simulate_od_scenario(
        ODScenario(
            scenarioId="phase9-public",
            requestedBy="pytest",
            mode="OFFENSE_EMULATION",
            environment="public_internet",
            scope=["example-scope"],
        )
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "EMULATION_REQUIRES_SYNTHETIC_OR_OWNED_LAB"


def test_defensive_production_request_is_read_only_plan():
    result = simulate_od_scenario(
        ODScenario(
            scenarioId="phase9-defense",
            requestedBy="pytest",
            mode="DEFENSE",
            environment="production",
            scope=["declared-production-scope"],
        )
    )
    assert result["status"] == "READY"
    assert result["executionMode"] == "READ_ONLY_DEFENSIVE_PLAN"
    assert result["offensePlan"] == []
    assert result["defensePlan"]
    assert result["externalExecutionPerformed"] is False


def test_mutation_requires_explicit_approval():
    result = simulate_od_scenario(
        ODScenario(
            scenarioId="phase9-mutation",
            requestedBy="pytest",
            mode="DEFENSE",
            environment="owned_test",
            scope=["owned-test-fixture"],
            mutation=True,
        )
    )
    assert result["status"] == "APPROVAL_REQUIRED"


def test_black_house_api_exposes_phase_9():
    client = TestClient(app)
    status = client.get("/api/black-house/status")
    assert status.status_code == 200
    assert status.json()["phases"]["9"] == "COMPLETE"
    assert status.json()["odPlane"]["execution"] == "PLAN_OR_SIMULATION_ONLY"

    od_status = client.get("/api/black-house/od")
    assert od_status.status_code == 200
    assert od_status.json()["offense"]["liveExploitation"] is False

    simulation = client.post(
        "/api/black-house/od/simulate",
        json={
            "scenarioId": "api-lab",
            "requestedBy": "pytest-api",
            "mode": "FULL_LOOP",
            "environment": "synthetic",
            "scope": ["synthetic-fixture"],
        },
    )
    assert simulation.status_code == 200
    assert simulation.json()["status"] == "READY"
