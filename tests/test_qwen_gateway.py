from __future__ import annotations

import json
import urllib.error

import pytest

from agents import qwen_gateway


def _clear_scale_env(monkeypatch):
    monkeypatch.delenv("QWEN_BASE_URLS", raising=False)
    monkeypatch.delenv("GPT_DOUG_PROVIDER_MAX_INFLIGHT", raising=False)
    monkeypatch.delenv("GPT_DOUG_PROVIDER_RETRIES", raising=False)
    monkeypatch.delenv("GPT_DOUG_PROVIDER_COOLDOWN", raising=False)
    qwen_gateway._reset_pool_state()


def test_local_qwen_gateway_requires_no_key(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv("QWEN_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_MODEL", raising=False)

    state = qwen_gateway.health()

    assert state["configured"] is True
    assert state["local"] is True
    assert state["model"] == "Qwen/Qwen3.8-Flash-Next"
    assert state["free"] is True
    assert state["replicas"] == 1


def test_remote_qwen_gateway_requires_key(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv("QWEN_BASE_URL", qwen_gateway.DEFAULT_REMOTE_BASE_URL)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    state = qwen_gateway.health()

    assert state["configured"] is False
    assert state["local"] is False


def test_insecure_non_loopback_http_is_rejected():
    with pytest.raises(ValueError):
        qwen_gateway._validate_base_url("http://example.com/v1")


def test_replica_pool_is_deduplicated(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv(
        "QWEN_BASE_URLS",
        "http://127.0.0.1:8000/v1,http://localhost:8001/v1,http://127.0.0.1:8000/v1",
    )
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    state = qwen_gateway.health()

    assert state["configured"] is True
    assert state["replicas"] == 2
    assert state["base_urls"] == [
        "http://127.0.0.1:8000/v1",
        "http://localhost:8001/v1",
    ]


def test_chat_once_parses_openai_compatible_response(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv("QWEN_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("QWEN_MODEL", "Qwen/Qwen3.8-Flash-Next")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"action":"finish","verify_command":"true"}',
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setattr(qwen_gateway.urllib.request, "urlopen", fake_urlopen)

    result = qwen_gateway.chat_once(
        [{"role": "user", "content": "test"}],
        options={"temperature": 0, "max_tokens": 100},
    )

    assert result["provider"] == "qwen"
    assert result["model"] == "Qwen/Qwen3.8-Flash-Next"
    assert result["endpoint"] == "http://127.0.0.1:8000/v1"
    assert captured["url"].endswith("/chat/completions")
    assert captured["body"]["max_tokens"] == 100


def test_chat_once_fails_over_to_next_replica(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv(
        "QWEN_BASE_URLS",
        "http://127.0.0.1:8000/v1,http://127.0.0.1:8001/v1",
    )
    monkeypatch.setenv("GPT_DOUG_PROVIDER_RETRIES", "1")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
            ).encode("utf-8")

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if request.full_url.startswith("http://127.0.0.1:8000/"):
            raise urllib.error.URLError("replica down")
        return Response()

    monkeypatch.setattr(qwen_gateway.urllib.request, "urlopen", fake_urlopen)

    result = qwen_gateway.chat_once([{"role": "user", "content": "test"}])

    assert len(calls) == 2
    assert result["endpoint"] == "http://127.0.0.1:8001/v1"
    assert result["message"]["content"] == "ok"


def test_replica_pool_round_robins_equal_load(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv(
        "QWEN_BASE_URLS",
        "http://127.0.0.1:8000/v1,http://127.0.0.1:8001/v1",
    )
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
            ).encode("utf-8")

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        return Response()

    monkeypatch.setattr(qwen_gateway.urllib.request, "urlopen", fake_urlopen)

    qwen_gateway.chat_once([{"role": "user", "content": "one"}])
    qwen_gateway.chat_once([{"role": "user", "content": "two"}])

    assert calls[0].startswith("http://127.0.0.1:8000/")
    assert calls[1].startswith("http://127.0.0.1:8001/")


def test_per_replica_inflight_limit(monkeypatch):
    _clear_scale_env(monkeypatch)
    monkeypatch.setenv("GPT_DOUG_PROVIDER_MAX_INFLIGHT", "1")
    endpoints = ["http://127.0.0.1:8000/v1"]

    first = qwen_gateway._acquire_endpoint(endpoints)
    second = qwen_gateway._acquire_endpoint(endpoints)

    assert first == endpoints[0]
    assert second is None

    qwen_gateway._release_endpoint(first)
