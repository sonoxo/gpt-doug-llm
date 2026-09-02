from fastapi.testclient import TestClient

from va3lm.app import app
from va3lm.max_memory import CompactMemory, memory_manager


def test_repeated_observation_consolidates_instead_of_growing():
    memory = CompactMemory("repeat", max_items=8, max_chars=2400)
    memory.add("Always run tests before deployment", kind="user")
    memory.add("Always run tests before deployment", kind="user")
    assert len(memory.records) == 1
    assert memory.records[0].hits == 2
    assert memory.status()["observations"] == 2


def test_memory_stays_bounded_and_retrieves_relevant_state():
    memory = CompactMemory("bounded", max_items=4, max_chars=1200)
    for index in range(12):
        memory.add(f"Task {index}: implement module {index} with tests and verification", kind="user")
    memory.add("Palantir writes require explicit authorization and human review", kind="policy", importance=1.0)
    assert len(memory.records) <= 4
    context = memory.context("Palantir authorization review")
    assert "Palantir writes require explicit authorization" in context
    assert memory.status()["compressionRatio"] >= 1.0


def test_api_uses_separate_memory_sessions():
    memory_manager.clear("alpha")
    memory_manager.clear("beta")
    client = TestClient(app)

    first = client.post("/api/brain", json={"text": "remember alpha deployment tests", "session_id": "alpha"})
    second = client.post("/api/brain", json={"text": "remember beta ontology review", "session_id": "beta"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["memory"]["sessionId"] == "alpha"
    assert second.json()["memory"]["sessionId"] == "beta"

    alpha = client.get("/api/memory/alpha?query=deployment").json()
    beta = client.get("/api/memory/beta?query=ontology").json()
    assert any("alpha deployment" in item["text"] for item in alpha["records"])
    assert any("beta ontology" in item["text"] for item in beta["records"])

    cleared = client.delete("/api/memory/alpha").json()
    assert cleared["cleared"] is True
    assert client.get("/api/memory/alpha").json()["status"]["records"] == 0
