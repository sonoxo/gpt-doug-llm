"""GPT-DOUG-ASTRA model orchestration primitives.

ASTRA does not pretend that every model is connected. It ranks only providers
that pass the existing runtime readiness contract and then routes a request to
the strongest available provider for the requested task profile.

The router is deliberately model-version agnostic: provider model names come
from each provider's existing environment configuration, so upgrading a model
never requires changing ASTRA's routing code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable


TASK_PROFILES = {
    "general": {"reasoning": 1.0, "coding": 0.6, "speed": 0.5, "multimodal": 0.3},
    "reasoning": {"reasoning": 1.0, "coding": 0.5, "speed": 0.2, "multimodal": 0.2},
    "coding": {"reasoning": 0.7, "coding": 1.0, "speed": 0.4, "multimodal": 0.1},
    "fast": {"reasoning": 0.3, "coding": 0.3, "speed": 1.0, "multimodal": 0.2},
    "vision": {"reasoning": 0.5, "coding": 0.2, "speed": 0.4, "multimodal": 1.0},
}

# Baseline provider tendencies. These are routing priors, not claims that a
# provider/model is globally "best". Runtime overrides can tune them without a
# code change as model generations evolve.
PROVIDER_PRIORS = {
    "openai": {"reasoning": 0.95, "coding": 0.95, "speed": 0.80, "multimodal": 0.95},
    "claude": {"reasoning": 0.95, "coding": 0.95, "speed": 0.75, "multimodal": 0.80},
    "anthropic": {"reasoning": 0.95, "coding": 0.95, "speed": 0.75, "multimodal": 0.80},
    "gemini": {"reasoning": 0.90, "coding": 0.85, "speed": 0.90, "multimodal": 0.95},
    "ollama": {"reasoning": 0.65, "coding": 0.75, "speed": 0.70, "multimodal": 0.30},
}


@dataclass(frozen=True)
class RankedProvider:
    provider: object
    score: float
    state: dict


def _overrides() -> dict:
    raw = os.environ.get("GPT_DOUG_ASTRA_PROVIDER_SCORES", "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _profile(name: str | None) -> dict[str, float]:
    requested = (name or "general").strip().lower()
    return TASK_PROFILES.get(requested, TASK_PROFILES["general"])


def _provider_scores(name: str) -> dict[str, float]:
    base = dict(PROVIDER_PRIORS.get(name, TASK_PROFILES["general"]))
    override = _overrides().get(name)
    if isinstance(override, dict):
        for key, value in override.items():
            if key in base and isinstance(value, (int, float)):
                base[key] = max(0.0, min(float(value), 1.0))
    return base


def infer_task(messages: list[dict], options: dict | None = None) -> str:
    options = options or {}
    explicit = options.get("astra_task") or options.get("task")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().lower()

    text = " ".join(str(item.get("content", "")) for item in messages[-6:]).lower()
    if any(token in text for token in ("image", "vision", "screenshot", "photo", "diagram")):
        return "vision"
    if any(token in text for token in ("code", "bug", "function", "typescript", "python", "javascript", "repo", "github")):
        return "coding"
    if any(token in text for token in ("quick", "fast", "speed", "brief", "short answer")):
        return "fast"
    if any(token in text for token in ("reason", "analyze", "prove", "derive", "compare", "strategy")):
        return "reasoning"
    return "general"


def rank_ready_providers(
    providers: Iterable[object],
    messages: list[dict],
    options: dict | None = None,
) -> list[RankedProvider]:
    task = infer_task(messages, options)
    profile = _profile(task)
    ranked: list[RankedProvider] = []

    for provider in providers:
        state = provider.health()
        if not (state.get("configured") and state.get("model_available")):
            continue
        name = str(getattr(provider.config, "name", state.get("provider", ""))).lower()
        scores = _provider_scores(name)
        weighted = sum(profile[key] * scores.get(key, 0.0) for key in profile)
        divisor = sum(profile.values()) or 1.0
        ranked.append(RankedProvider(provider=provider, score=weighted / divisor, state=state))

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def astra_health(providers: Iterable[object]) -> dict:
    states = [provider.health() for provider in providers]
    ready = [state for state in states if state.get("configured") and state.get("model_available")]
    return {
        "backend": "astra",
        "provider": "astra",
        "configured": bool(ready),
        "model": "gpt-doug-astra",
        "model_available": bool(ready),
        "models": [state.get("model") for state in ready if state.get("model")],
        "providers": states,
        "ready_provider_count": len(ready),
        "upgrade_policy": "model-version-agnostic",
        "authorization_policy": "route-ready-providers-only",
        "message": (
            f"GPT-DOUG-ASTRA ready with {len(ready)} authorized provider(s)"
            if ready
            else "GPT-DOUG-ASTRA has no authorized ready provider"
        ),
    }
