import threading
import time
from http.server import ThreadingHTTPServer

import pytest

from body_link.client import BodyLinkClient
from body_link.protocol import canonical_json, normalize_runtime_url, sign, verify
from body_link.server import Handler


def test_replit_workspace_url_is_not_treated_as_runtime_endpoint():
    with pytest.raises(ValueError, match="workspace URLs are not runtime endpoints"):
        normalize_runtime_url("https://replit.com/@24kmediaproduct/GPT-Doug-AI-Hub")


def test_https_runtime_url_is_accepted():
    assert (
        normalize_runtime_url("https://gpt-doug-ai-hub.replit.app/")
        == "https://gpt-doug-ai-hub.replit.app"
    )


def test_local_http_runtime_is_accepted_for_development():
    assert normalize_runtime_url("http://127.0.0.1:3000") == "http://127.0.0.1:3000"


def test_signed_protocol_round_trip():
    secret = "x" * 32
    body = canonical_json({"controller_id": "GPT_DOUG"})
    timestamp = str(int(time.time()))
    nonce = "abc123"
    signature = sign(
        secret,
        method="POST",
        path="/v1/handshake",
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )
    assert verify(
        secret,
        method="POST",
        path="/v1/handshake",
        timestamp=timestamp,
        nonce=nonce,
        body=body,
        signature=signature,
    )


def test_signature_rejects_modified_body():
    secret = "x" * 32
    timestamp = str(int(time.time()))
    signature = sign(
        secret,
        method="POST",
        path="/v1/handshake",
        timestamp=timestamp,
        nonce="n1",
        body=b"{}",
    )
    assert not verify(
        secret,
        method="POST",
        path="/v1/handshake",
        timestamp=timestamp,
        nonce="n1",
        body=b'{"changed":true}',
        signature=signature,
    )


def test_client_and_body_node_complete_signed_handshake_and_heartbeat(tmp_path, monkeypatch):
    secret = "s" * 40
    monkeypatch.setenv("GPT_DOUG_BODY_LINK_KEY", secret)
    monkeypatch.setenv("GPT_DOUG_BODY_NODE_ID", "replit:test/GPT-Doug-AI-Hub")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = BodyLinkClient(
            f"http://{host}:{port}",
            secret,
            state_dir=tmp_path,
            hive_id="hive-test",
            ontology_hash="ontology-test",
        )
        linked = client.link()
        assert linked["linked"] is True
        assert linked["body_node_id"] == "replit:test/GPT-Doug-AI-Hub"

        heartbeat = client.ping()
        assert heartbeat["status"] == "ONLINE"
        assert heartbeat["remote_shell"] is False

        status = client.status()
        assert status["linked"] is True
        assert status["body_node_id"] == "replit:test/GPT-Doug-AI-Hub"
        assert status["secrets_persisted"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
