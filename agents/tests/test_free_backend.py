import os, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

class TestFreeOnlyBackend:
    def test_openai_blocked_by_default(self):
        os.environ.pop("PAID_MODE", None)
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import PAID_MODE, FREE_ONLY
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
        assert "Install Ollama" in result["message"]["content"]

    def test_health_reports_free(self):
        os.environ.pop("PAID_MODE", None)
        sys.modules.pop("agents.llm_backend_free", None)
        from agents.llm_backend_free import health
        h = health()
        assert "free" in h
        assert "paid_mode" in h

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
