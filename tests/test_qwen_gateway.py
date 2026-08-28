from __future__ import annotations

import json

import pytest

from agents import qwen_gateway


def test_local_qwen_gateway_requires_no_key(monkeypatch):
    monkeypatch.setenv("QWEN_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_MODEL", raising=False)

    state = qwen_gateway.health()

    assert state["configured"] is True
    assert state["local"] is True
    assert state["model"] == "Qwen/Qwen3.8-Flash-Next"
    assert state["free"] is True


def test_remote_qwen_gateway_requires_key(monkeypatch):
    monkeypatch.setenv("QWEN_BASE_URL", qwen_gateway.DEFAULT_REMOTE_BASE_URL)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    state = qwen_gateway.health()

    assert state["configured"] is False
    assert state["local"] is False


def test_insecure_non_loopback_http_is_rejected():
    with pytest.raises(ValueError):
        qwen_gateway._validate_base_url("http://example.com/v1")


def test_chat_once_parses_openai_compatible_response(monkeypatch):
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
    assert captured["url"].endswith("/chat/completions")
    assert captured["body"]["max_tokens"] == 100
