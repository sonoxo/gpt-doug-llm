import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from pineal.http_api import PinealHTTPServer
from pineal.store import PinealStore

TOKEN = "unit-test-long-enough-secret-token-123456789"


@pytest.fixture
def api(tmp_path):
    server = PinealHTTPServer(("127.0.0.1", 0), PinealStore(tmp_path / "db.sqlite3"), TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def send(url, path, *, method="GET", payload=None, auth=True):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(url + path, headers=headers, method=method, data=body)
    with urlopen(req, timeout=5) as response:
        return response.status, json.load(response)


def test_auth_and_memory_lifecycle(api):
    with pytest.raises(HTTPError) as exc:
        send(api, "/v1/health", auth=False)
    assert exc.value.code == 401
    _, health = send(api, "/v1/health")
    assert health["model_weights_access"] is False
    status, record = send(api, "/v1/memories", method="POST", payload={
        "subject": "gpt-doug", "predicate": "has_component", "value": "pineal", "source": "test"})
    assert status == 201
    _, recalled = send(api, "/v1/context?q=pineal")
    assert recalled["pineal_memory"][0]["id"] == record["id"]
    _, updated = send(api, f"/v1/memories/{record['id']}", method="PUT", payload={
        "expected_version": 1, "subject": "gpt-doug", "predicate": "has_component",
        "value": "kraken", "source": "test"})
    assert updated["version"] == 2
    _, deleted = send(api, f"/v1/memories/{record['id']}?expected_version=2", method="DELETE")
    assert deleted["deleted"] == record["id"]
    assert send(api, "/v1/audit/verify")[1]["ok"]


def test_telemetry_does_not_actuate(api):
    _, res = send(api, "/v1/telemetry", method="POST", payload={
        "temperature_c": 94, "power_w": 200, "water_fraction": 0.7})
    assert res["advisory"]["mode"] == "safe_stop"
    assert not res["advisory"]["actuated"]
    assert send(api, "/v1/telemetry")[1]["latest"]["mode"] == "safe_stop"


def test_loopback_only(tmp_path):
    with pytest.raises(ValueError):
        PinealHTTPServer(("0.0.0.0", 0), PinealStore(tmp_path / "db.sqlite3"), TOKEN)


def test_post_cannot_change_existing_memory(api):
    _, original = send(api, "/v1/memories", method="POST", payload={
        "subject": "mine", "predicate": "purpose", "value": "original", "source": "human"})
    with pytest.raises(HTTPError) as exc:
        send(api, "/v1/memories", method="POST", payload={
            "item_id": original["id"], "expected_version": 1,
            "subject": "mine", "predicate": "purpose", "value": "malicious", "source": "human"})
    assert exc.value.code == 400
    assert send(api, f"/v1/memories/{original['id']}")[1]["value"] == "original"
