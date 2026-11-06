"""Measured local SKULL-LLM benchmark, never a claim of model intelligence.

Offline unless explicitly invoked by the operator. Calls the existing
local-only SkullEngine; respects the same emergency stop and bounded depth.
No cloud providers, hidden prompts, test answer logs, or token-rate estimates.
"""
from __future__ import annotations

import math
import statistics
import time
from typing import Any, Callable

from ai_killswitch import require_ai_allowed

from .runtime import SkullConfig, SkullEngine

DEFAULT_PROMPT = "In one sentence, define a knowledge graph."


def benchmark(
    *,
    prompt: str = DEFAULT_PROMPT,
    repetitions: int = 1,
    model: str | None = None,
    engine_factory: Callable[..., Any] = SkullEngine,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    if not 1 <= repetitions <= 5:
        raise ValueError("repetitions must be 1..5")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 400:
        raise ValueError("prompt must contain 1..400 characters")
    if model is not None and (not isinstance(model, str) or len(model) > 180):
        raise ValueError("model identifier exceeds limit")

    samples: list[float] = []
    response_lengths: list[int] = []
    calls = 0
    # Real model execution, intentionally not storing private prompts/answers.
    for _ in range(repetitions):
        require_ai_allowed("SKULL-LLM local benchmark")
        engine = engine_factory(config=SkullConfig(model=model, depth=1, remember=False))
        started = clock()
        result = engine.run(prompt.strip())
        elapsed = clock() - started
        require_ai_allowed("SKULL-LLM benchmark result")
        if not isinstance(elapsed, (float, int)) or not math.isfinite(elapsed) or elapsed < 0:
            raise RuntimeError("benchmark timer returned invalid elapsed time")
        if not isinstance(result.answer, str):
            raise RuntimeError("benchmark response was not text")
        samples.append(elapsed * 1000)
        response_lengths.append(len(result.answer))
        calls += result.calls

    samples_sorted = sorted(samples)
    return {
        "system": "SKULL-LLM",
        "benchmark": "local-inference-latency",
        "real_model_requests": True,
        "model": model or "ollama-default",
        "repetitions": repetitions,
        "depth": 1,
        "model_calls": calls,
        "min_ms": round(samples_sorted[0], 3),
        "median_ms": round(statistics.median(samples_sorted), 3),
        "p95_ms": round(samples_sorted[math.ceil(repetitions * 0.95) - 1], 3),
        "max_ms": round(samples_sorted[-1], 3),
        "response_chars": response_lengths,
        "contains_prompt_or_answers": False,
        "token_throughput_measured": False,
        "note": "Latency is observed locally; response length is characters, not tokens.",
    }
