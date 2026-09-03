from fastapi.testclient import TestClient

from va3lm.app import app
from va3lm.black_house_api import reset_runtime_for_tests
from va3lm.ecosystem_telemetry import collect_fleet
from va3lm.mission_ledger import MissionLedger
from va3lm.rvia import MissionEnvelope, RVIARouter


def test_rvia_routes_local_and_contract_targets(tmp_path):
    ledger = MissionLedger(tmp_path / "missions.db")
    router = RVIARouter(ledger)

    local = router.route(
        MissionEnvelope(
            requestedBy="pytest",
            intent="Build a bounded plan with evidence",
            target="GPT_DOUG_MAX",
        )
    )
    assert local["status"] == "COMPLETED"
    assert local["mission"]["result"]["executionState"] == "LOCAL_PLAN_COMPLETE"

    contract = router.route(
        MissionEnvelope(
            requestedBy="pytest",
            intent="Hand this mission to XUNIA",
            target="XUNIA",
            requiredCapabilities=["orchestration"],
        )
    )
    assert contract["status"] == "COMPLETED"
    assert contract["mission"]["result"]["executionState"] == "MISSION_CONTRACT_ACCEPTED"
    assert ledger.summary()["missions"] == 2


def test_rvia_fails_closed_on_mutation_and_unverified_palantir(tmp_path):
    router = RVIARouter(MissionLedger(tmp_path / "missions.db"))

    mutation = router.route(
        MissionEnvelope(
            requestedBy="pytest",
            intent="Deploy an approved artifact",
            target="ZYRA_CLOUD",
            mutation=True,
        )
    )
    assert mutation["status"] == "APPROVAL_REQUIRED"

    palantir = router.route(
        MissionEnvelope(
            requestedBy="pytest",
            intent="Read live ontology",
            target="PALANTIR",
            metadata={"requiresLive": True},
        )
    )
    assert palantir["status"] == "HOLD"
    assert palantir["mission"]["result"]["executionState"] == "LIVE_TENANT_UNVERIFIED"


def test_mission_ledger_preserves_timeline(tmp_path):
    ledger = MissionLedger(tmp_path / "missions.db")
    router = RVIARouter(ledger)
    result = router.route(
        MissionEnvelope(
            requestedBy="pytest",
            intent="Inspect security policy",
            target="ZYRA",
            requiredCapabilities=["policy"],
        )
    )
    timeline = ledger.timeline(result["mission"]["missionId"])
    event_types = [event["eventType"] for event in timeline]
    assert event_types[0] == "MISSION_RECEIVED"
    assert "SHADOW_GLASS_POLICY" in event_types
    assert "ZYRA_AUTHORIZATION" in event_types
    assert "GLASS_ONION_EVIDENCE" in event_types
    assert event_types[-1] == "MISSION_FINALIZED"


def test_telemetry_declared_mode_is_deterministic():
    payload = collect_fleet(["sonoxo/gpt-doug-llm", "sonoxo/zyra"], live=False)
    assert payload["live"] is False
    assert payload["overall"] == "DECLARED"
    assert len(payload["repositories"]) == 2


def test_command_center_runtime_surface(tmp_path, monkeypatch):
    monkeypatch.setenv("BLACK_HOUSE_LEDGER_PATH", str(tmp_path / "api-missions.db"))
    reset_runtime_for_tests()
    client = TestClient(app)

    routed = client.post(
        "/api/black-house/missions",
        json={
            "requestedBy": "pytest-api",
            "intent": "Route a mission through the Black House",
            "target": "XUNIA",
            "classification": "INTERNAL",
        },
    )
    assert routed.status_code == 200
    assert routed.json()["status"] == "COMPLETED"

    history = client.get("/api/black-house/missions")
    assert history.status_code == 200
    assert history.json()["summary"]["missions"] == 1

    manifest = client.get("/api/black-house/router").json()
    assert manifest["protocol"] == "black-house-mission-v1"
    assert manifest["failClosed"] is True

    page = client.get("/black-house")
    assert page.status_code == 200
    assert "THE BLACK HOUSE" in page.text
    assert "MISSION CONSOLE" in page.text
