from __future__ import annotations

import urllib.error

from agents.llm_backend import AnthropicProvider
from agents.mythos_bridge import FABLE_MODEL, MYTHOS_MODEL, MythosProvider


def _configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-long-enough")
    return MythosProvider()


def test_mythos_profile_targets_mythos(monkeypatch):
    provider = _configured(monkeypatch)
    state = provider.health()
    assert provider.config.name == "mythos"
    assert provider.config.model == MYTHOS_MODEL
    assert state["model"] == MYTHOS_MODEL
    assert state["fallback_model"] == FABLE_MODEL
    assert state["mythos_access"] == "anthropic_authorization_required"


def test_mythos_request_uses_target_model(monkeypatch):
    provider = _configured(monkeypatch)
    calls = []

    def fake_chat(self, messages, model, options):
        calls.append(model)
        return {
            "model": model,
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
            "provider": "claude",
        }

    monkeypatch.setattr(AnthropicProvider, "chat_once", fake_chat)
    result = provider.chat_once([{"role": "user", "content": "hello"}], None, {})

    assert calls == [MYTHOS_MODEL]
    assert result["provider"] == "mythos"
    assert result["requested_model"] == MYTHOS_MODEL
    assert result["fallback_used"] is False


def test_mythos_falls_back_to_fable_on_access_error(monkeypatch):
    provider = _configured(monkeypatch)
    calls = []

    def fake_chat(self, messages, model, options):
        calls.append(model)
        if model == MYTHOS_MODEL:
            raise urllib.error.HTTPError(
                url="https://api.anthropic.com/v1/messages",
                code=403,
                msg="forbidden",
                hdrs=None,
                fp=None,
            )
        return {
            "model": model,
            "message": {"role": "assistant", "content": "fallback"},
            "done": True,
            "provider": "claude",
        }

    monkeypatch.setattr(AnthropicProvider, "chat_once", fake_chat)
    result = provider.chat_once([{"role": "user", "content": "hello"}], None, {})

    assert calls == [MYTHOS_MODEL, FABLE_MODEL]
    assert result["model"] == FABLE_MODEL
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "mythos_http_403"


def test_mythos_fallback_can_be_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-long-enough")
    monkeypatch.setenv("ANTHROPIC_MYTHOS_FALLBACK", "0")
    provider = MythosProvider()

    def fake_chat(self, messages, model, options):
        raise urllib.error.HTTPError(
            url="https://api.anthropic.com/v1/messages",
            code=403,
            msg="forbidden",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(AnthropicProvider, "chat_once", fake_chat)

    try:
        provider.chat_once([{"role": "user", "content": "hello"}], None, {})
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    else:
        raise AssertionError("expected Anthropic access error")
