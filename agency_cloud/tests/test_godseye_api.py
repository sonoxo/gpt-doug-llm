from fastapi import FastAPI
from fastapi.testclient import TestClient

import agency_cloud.godseye_api as api


class FakeSnapshot:
    def to_dict(self):
        return {
            "schema": "gpt-doug.godseye-snapshot.v1",
            "generated_at": "2026-10-07T20:00:00+00:00",
            "policy": {"mode": "READ_ONLY_FUSION"},
            "subsystems": {},
            "provenance": [],
            "uncertainty": [],
        }


def _client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_godseye_status_and_sources(monkeypatch):
    monkeypatch.setattr(api, "collect_snapshot", lambda: FakeSnapshot())
    monkeypatch.setattr(api, "snapshot_sources", lambda snapshot: [{"subsystem": "global_intel", "id": "cisa-kev"}])
    client = _client()

    status = client.get("/api/v1/godseye/status")
    sources = client.get("/api/v1/godseye/sources")

    assert status.status_code == 200
    assert status.json()["schema"] == "gpt-doug.godseye-snapshot.v1"
    assert sources.status_code == 200
    assert sources.json() == {"schema": "gpt-doug.godseye-sources.v1", "sources": [{"subsystem": "global_intel", "id": "cisa-kev"}]}


def test_godseye_query_allowed(monkeypatch):
    class Engine:
        def query(self, question):
            return {
                "schema": "gpt-doug.godseye-query.v1",
                "status": "COMPLETE",
                "question": question,
                "answer": "safe",
                "policy": {"decision": "ALLOW_READ_ONLY"},
            }

    monkeypatch.setattr(api, "query_engine_factory", Engine)
    response = _client().post("/api/v1/godseye/query", json={"question": "show health"})
    assert response.status_code == 200
    assert response.json()["answer"] == "safe"


def test_godseye_query_denies_blocked_request(monkeypatch):
    class Engine:
        def query(self, question):
            return {
                "schema": "gpt-doug.godseye-query.v1",
                "status": "BLOCKED",
                "question": question,
                "answer": "blocked",
                "policy": {"decision": "BLOCK"},
            }

    monkeypatch.setattr(api, "query_engine_factory", Engine)
    response = _client().post("/api/v1/godseye/query", json={"question": "autonomous target selection"})
    assert response.status_code == 403
    assert response.json()["detail"]["policy"]["decision"] == "BLOCK"


def test_query_and_plan_validate_empty_body():
    client = _client()
    assert client.post("/api/v1/godseye/query", json={"question": ""}).status_code == 422
    assert client.post("/api/v1/planetary/plan", json={"mission": ""}).status_code == 422


def test_planetary_routes(monkeypatch):
    monkeypatch.setattr(api, "planetary_status", lambda: {"schema": "gpt-doug.planetary-status.v1", "status": "ONLINE", "sources": []})
    monkeypatch.setattr(api, "planetary_layers", lambda status: [{"id": "public-space"}])
    monkeypatch.setattr(api, "planetary_plan", lambda mission: {"schema": "gpt-doug.planetary-plan.v1", "mission": mission})
    client = _client()

    status = client.get("/api/v1/planetary/status")
    layers = client.get("/api/v1/planetary/layers")
    plan = client.post("/api/v1/planetary/plan", json={"mission": "compare layers"})

    assert status.status_code == 200
    assert status.json()["schema"] == "gpt-doug.planetary-status.v1"
    assert layers.json() == {"schema": "gpt-doug.planetary-layers.v1", "layers": [{"id": "public-space"}]}
    assert plan.json()["mission"] == "compare layers"


def test_runtime_adapter_failure_returns_503(monkeypatch):
    def broken():
        raise RuntimeError("internal detail")

    monkeypatch.setattr(api, "collect_snapshot", broken)
    response = _client().get("/api/v1/godseye/status")
    assert response.status_code == 503
    assert response.json()["detail"] == "GoDsEye subsystem unavailable"
