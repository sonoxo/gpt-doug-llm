import importlib.util

from agents.llm_backend import (
    PROVIDER_FACTORIES,
    QwenMLXProvider,
)


def test_qwen_registered():
    assert "qwen" in PROVIDER_FACTORIES
    assert "mlx" in PROVIDER_FACTORIES
    assert PROVIDER_FACTORIES["qwen"] is QwenMLXProvider


def test_qwen_provider_configuration():
    provider = QwenMLXProvider()

    assert provider.config.name == "qwen"
    assert "Qwen" in provider.config.model
    assert provider.config.free is True


def test_qwen_is_local_mlx():
    provider = QwenMLXProvider()
    status = provider.health()

    assert status["provider"] == "qwen"
    assert status["runtime"] == "mlx"
    assert status["local"] is True
    assert status["ollama"] is False


def test_mlx_environment_present():
    assert importlib.util.find_spec("mlx_lm") is not None
