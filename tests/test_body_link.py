import time

import pytest

from body_link.protocol import canonical_json, normalize_runtime_url, sign, verify


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
