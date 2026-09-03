from __future__ import annotations

from dataclasses import dataclass

from agents.astra_router import astra_health, infer_task, rank_ready_providers


@dataclass
class _Config:
    name: str
    model: str


class _Provider:
    def __init__(self, name: str, model: str, *, ready: bool = True):
        self.config = _Config(name, model)
        self._ready = ready

    def health(self):
        return {
            "provider": self.config.name,
            "configured": self._ready,
            "model": self.config.model,
            "model_available": self._ready,
        }


def test_infer_task_detects_coding():
    assert infer_task([{"role": "user", "content": "Fix this Python function and GitHub repo bug"}]) == "coding"


def test_explicit_task_wins_over_inference():
    messages = [{"role": "user", "content": "Fix this Python function"}]
    assert infer_task(messages, {"astra_task": "reasoning"}) == "reasoning"


def test_rank_excludes_unready_provider():
    providers = [
        _Provider("openai", "configured-model", ready=True),
        _Provider("claude", "unavailable-model", ready=False),
    ]
    ranked = rank_ready_providers(providers, [{"role": "user", "content": "Analyze this strategy"}])
    assert [candidate.provider.config.name for candidate in ranked] == ["openai"]


def test_health_never_claims_unready_provider_connected():
    state = astra_health([_Provider("openai", "model-a", ready=False)])
    assert state["configured"] is False
    assert state["model_available"] is False
    assert state["ready_provider_count"] == 0
    assert state["authorization_policy"] == "route-ready-providers-only"


def test_health_reports_ready_models_without_version_locking():
    state = astra_health([
        _Provider("openai", "future-openai-model", ready=True),
        _Provider("gemini", "future-gemini-model", ready=True),
    ])
    assert state["configured"] is True
    assert state["ready_provider_count"] == 2
    assert state["models"] == ["future-openai-model", "future-gemini-model"]
    assert state["upgrade_policy"] == "model-version-agnostic"
