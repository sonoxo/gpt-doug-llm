from __future__ import annotations

from fastapi.testclient import TestClient

from va3lm.app import app
from va3lm.green_house import green_house_status


def test_green_house_runtime_loader_is_mounted():
    state = green_house_status()
    assert state["runtimeMounted"] is True
    assert state["runtimeState"] == "RUNTIME_MOUNTED"
    assert state["parentControlPlane"] == "THE_BLACK_HOUSE_V1"
    assert state["domains"] == ["eco", "bio", "pharma", "fda"]


def test_black_house_exposes_green_house_layer():
    client = TestClient(app)
    response = client.get("/api/black-house/green-house")
    assert response.status_code == 200
    state = response.json()
    assert state["runtimeMounted"] is True
    assert state["layerId"] == "THE_GREEN_HOUSE_V1"

    black_house = client.get("/api/black-house/status")
    assert black_house.status_code == 200
    payload = black_house.json()
    assert payload["layers"]["greenHouse"]["runtimeState"] == "RUNTIME_MOUNTED"
