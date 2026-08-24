import importlib
import os
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestFreeOnlyBackend:
    def test_default_provider_never_touches_network(self, monkeypatch):
        monkeypatch.delenv("GPT_DOUG_PROVIDER", raising=False)
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *args, **kwargs: pytest.fail(f"default startup attempted network access: {args}"),
        )
        sys.modules.pop("agents.llm_backend", None)
        backend = importlib.import_module("agents.llm_backend")
        assert backend.health()["provider"] == "none"
        assert backend.chat_once([{"role": "user", "content": "hello"}])["offline"] is True

    def test_ollama_requires_explicit_provider_selection(self, monkeypatch):
        monkeypatch.delenv("GPT_DOUG_PROVIDER", raising=False)
        sys.modules.pop("agents.llm_backend", None)
        backend = importlib.import_module("agents.llm_backend")
        assert backend.health()["provider"] != "ollama"

    def test_openai_blocked_by_default(self):
        os.environ.pop("PAID_MODE", None)
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import FREE_ONLY, PAID_MODE

        assert PAID_MODE is False
        assert FREE_ONLY is True

    def test_paid_mode_requires_explicit_opt_in(self):
        os.environ["PAID_MODE"] = "false"
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import PAID_MODE

        assert PAID_MODE is False
        os.environ["PAID_MODE"] = "true"
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import PAID_MODE as paid

        assert paid is True
        os.environ.pop("PAID_MODE", None)

    def test_no_backend_returns_error_not_paid(self):
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("PAID_MODE", None)
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import chat_once

        result = chat_once([{"role": "user", "content": "hello"}])
        assert "error" in result
        assert result["error"] == "provider_not_configured"
        assert "offline workspace mode" in result["message"]["content"]

    def test_health_reports_free(self):
        os.environ.pop("PAID_MODE", None)
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import health

        h = health()
        assert "free" in h
        assert "paid_mode" in h

    def test_provider_transport_rejects_non_network_scheme(self):
        from agents.llm_backend import _safe_urlopen

        request = urllib.request.Request("file:///tmp/provider-payload")
        with pytest.raises(ValueError, match="Refusing unsafe provider URL"):
            _safe_urlopen(request, timeout=1)

    def test_provider_transport_rejects_remote_plain_http(self):
        from agents.llm_backend import _safe_urlopen

        request = urllib.request.Request("http://example.com/api")
        with pytest.raises(ValueError, match="Refusing unsafe provider URL"):
            _safe_urlopen(request, timeout=1, allow_local_http=True)

    def test_provider_transport_allows_loopback_http(self, monkeypatch):
        from agents.llm_backend import _safe_urlopen

        sentinel = object()
        monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: sentinel)
        request = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        assert _safe_urlopen(request, timeout=1, allow_local_http=True) is sentinel


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
