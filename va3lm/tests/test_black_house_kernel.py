from fastapi.testclient import TestClient

from va3lm.app import app
from va3lm.ontology import CANONICAL_OBJECT_TYPES, CANONICAL_RELATIONSHIPS, kernel_status


def test_va3lm_is_bound_to_black_house_kernel_v3():
    status = kernel_status()
    assert status["status"] == "GREEN"
    assert status["version"] == "3.0.0"
    assert status["controlPlane"] == "THE_BLACK_HOUSE_V1"
    assert status["failClosed"] is True
    assert "Mission" in CANONICAL_OBJECT_TYPES
    assert "Evidence" in CANONICAL_OBJECT_TYPES
    assert "GOVERNS" in CANONICAL_RELATIONSHIPS


def test_api_exposes_canonical_kernel_binding():
    payload = TestClient(app).get("/api/ontology").json()
    assert payload["kernel"]["version"] == "3.0.0"
    assert payload["kernel"]["controlPlane"] == "THE_BLACK_HOUSE_V1"
    assert payload["kernel"]["failClosed"] is True
