from fastapi.testclient import TestClient
from va3lm.agents import roster
from va3lm.app import app
from va3lm.brain import ask
from va3lm.explainer import explain
from va3lm.ontology import schema
from va3lm.planner import build_plan


def test_agent_roster_and_plan():
    assert len(roster()) == 9
    plan = build_plan("add endpoint")
    assert plan["mutationGate"] == "HUMAN_APPROVAL_REQUIRED"
    assert plan["steps"][-2]["state"] == "BLOCKED_PENDING_APPROVAL"


def test_ontology_guardrails():
    ontology = schema()
    assert ontology["deploymentState"] == "BLUEPRINT_NOT_LIVE_FOUNDRY"
    assert ontology["guardrails"]["automaticPublish"] is False
    assert ontology["guardrails"]["humanApprovalForMutation"] is True


def test_brain_falls_back_without_endpoint(monkeypatch):
    monkeypatch.delenv("VA3LM_MODEL_URL", raising=False)
    result = ask("build tests")
    assert result["mode"] == "DETERMINISTIC_PLAN"


def test_explainer_has_required_beats():
    result = explain("VA3LM")
    assert [item["beat"] for item in result["beats"]] == [
        "HOOK",
        "WHAT",
        "HOW",
        "PROOF",
        "BENEFIT",
        "CTA",
    ]


def test_api_8088_identity_and_federal_intel_routes():
    client = TestClient(app)
    assert client.get("/healthz").json()["port"] == 8088
    status = client.get("/api/status").json()
    assert status["brain"] == "gpt-doug-llm"
    assert status["federalIntel"]["mode"] == "PUBLIC_OSINT_ONLY"
    assert status["federalIntel"]["entities"] == 5
    assert client.post("/api/explain", json={"text": "ontology"}).status_code == 200

    catalog = client.get("/api/federal-intel")
    assert catalog.status_code == 200
    assert [item["id"] for item in catalog.json()["entities"]] == ["cia", "nsa", "nro", "ngp", "gdip"]

    github = client.get("/api/federal-intel/github")
    assert github.status_code == 200
    assert {item["id"] for item in github.json()["sources"]} == {"nsa", "ngp"}

    assert client.get("/api/federal-intel/nsa").status_code == 200
    assert client.get("/api/federal-intel/unknown").status_code == 404
