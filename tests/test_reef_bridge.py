from reef_bridge import REEF_LIFECYCLE, ReefBridge, ReefBridgeError, ReefConfig


def test_lifecycle_is_ordered():
    assert REEF_LIFECYCLE == ("serve", "observe", "grow", "commit")


def test_ontology_registration_is_isolated_copy():
    first = ReefBridge.ontology_registration()
    second = ReefBridge.ontology_registration()

    assert first["upstream"]["license"] == "Apache-2.0"
    assert first["gpt_doug_mapping"]["Task"] == "AgentInteraction"
    first["lifecycle"].append("mutated")
    assert second["lifecycle"] == ["serve", "observe", "grow", "commit"]


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("REEF_BASE_URL", "http://reef.example:9999/")
    monkeypatch.setenv("REEF_TOKEN", "secret-token")
    monkeypatch.setenv("REEF_SCENARIO", "proof-cycle")
    monkeypatch.setenv("REEF_TIMEOUT", "12.5")

    config = ReefConfig.from_env()

    assert config.base_url == "http://reef.example:9999"
    assert config.token == "secret-token"
    assert config.scenario == "proof-cycle"
    assert config.timeout == 12.5


def test_transport_accepts_https_and_preserves_base_path():
    bridge = ReefBridge(ReefConfig(base_url="https://reef.example/runtime"))

    connection_class, host, port, path = bridge._connection_target("/healthz")

    assert connection_class.__name__ == "HTTPSConnection"
    assert host == "reef.example"
    assert port == 443
    assert path == "/runtime/healthz"


def test_transport_rejects_non_http_schemes():
    for base_url in ("file:///tmp/reef", "ftp://reef.example", "gopher://reef.example"):
        bridge = ReefBridge(ReefConfig(base_url=base_url))
        try:
            bridge._connection_target("/healthz")
        except ReefBridgeError as exc:
            assert "http" in str(exc).lower()
        else:
            raise AssertionError(f"expected unsafe scheme to fail: {base_url}")


def test_transport_rejects_embedded_credentials():
    bridge = ReefBridge(ReefConfig(base_url="https://user:password@reef.example"))

    try:
        bridge._connection_target("/healthz")
    except ReefBridgeError as exc:
        assert "credentials" in str(exc).lower()
    else:
        raise AssertionError("expected embedded credentials to fail")


def test_transport_rejects_query_and_fragment():
    for base_url in (
        "https://reef.example?redirect=file:///tmp/reef",
        "https://reef.example/#fragment",
    ):
        bridge = ReefBridge(ReefConfig(base_url=base_url))
        try:
            bridge._connection_target("/healthz")
        except ReefBridgeError as exc:
            assert "query or fragment" in str(exc).lower()
        else:
            raise AssertionError(f"expected ambiguous base URL to fail: {base_url}")


def test_chat_completion_preserves_receipt(monkeypatch):
    bridge = ReefBridge(ReefConfig())

    def fake_request(method, path, payload=None):
        assert method == "POST"
        assert path == "/v1/chat/completions"
        assert payload["model"] == "test-model"
        return {
            "status": 200,
            "headers": {"x-reef-agent-record-id": "receipt-123"},
            "body": {"choices": [{"message": {"content": "ready"}}]},
        }

    monkeypatch.setattr(bridge, "_request", fake_request)
    completion = bridge.chat_completion(
        model="test-model",
        messages=[{"role": "user", "content": "ready?"}],
    )

    assert completion["receipt_id"] == "receipt-123"
    assert completion["http_status"] == 200


def test_feedback_uses_completion_receipt(monkeypatch):
    bridge = ReefBridge(ReefConfig())
    captured = {}

    def fake_request(method, path, payload=None):
        captured.update({"method": method, "path": path, "payload": payload})
        return {"status": 200, "headers": {}, "body": {"accepted": True}}

    monkeypatch.setattr(bridge, "_request", fake_request)
    result = bridge.feedback_for_completion(
        {"receipt_id": "receipt-abc"},
        score=1.0,
        feedback={"reason": "verified"},
    )

    assert captured == {
        "method": "POST",
        "path": "/reef/report",
        "payload": {
            "references": ["receipt-abc"],
            "score": 1.0,
            "feedback": {"reason": "verified"},
        },
    }
    assert result["body"]["accepted"] is True


def test_feedback_requires_evidence():
    bridge = ReefBridge(ReefConfig())

    try:
        bridge.report(references=[], score=1.0)
    except ReefBridgeError as exc:
        assert "receipt" in str(exc).lower()
    else:
        raise AssertionError("expected missing receipt to fail")

    try:
        bridge.report(references=["receipt-1"])
    except ReefBridgeError as exc:
        assert "score" in str(exc).lower()
    else:
        raise AssertionError("expected missing feedback evidence to fail")
