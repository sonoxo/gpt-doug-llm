from __future__ import annotations

import os

from .types import Task, Candidate


def available_providers() -> list[str]:
    providers = ["offline"]

    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")

    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("anthropic")

    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        providers.append("gemini")

    return providers


def score_provider(provider: str, task: Task) -> Candidate:
    score = 0.0
    reasons: list[str] = []

    if provider == "offline":
        score += 0.35
        reasons.append("local orchestration available")

        if task.needs_tools:
            score += 0.20
            reasons.append("local tools")

        if task.needs_files:
            score += 0.15
            reasons.append("workspace inspection")

        if task.needs_security:
            score += 0.15
            reasons.append("defensive local inspection")

        if task.complexity > 0.70:
            score -= 0.15
            reasons.append("complex inference may benefit from cloud provider")

    elif provider == "openai":
        score += 0.78

        if task.needs_code:
            score += 0.14

        if task.needs_reasoning:
            score += 0.08

        reasons.append("general coding and reasoning")

    elif provider == "anthropic":
        score += 0.76

        if task.needs_code:
            score += 0.14

        if task.needs_reasoning:
            score += 0.08

        reasons.append("coding and long-context reasoning")

    elif provider == "gemini":
        score += 0.72

        if task.needs_reasoning:
            score += 0.10

        reasons.append("general reasoning")

    return Candidate(
        name=provider,
        score=max(0.0, min(score, 1.0)),
        reason="; ".join(reasons),
    )


def route(task: Task) -> list[Candidate]:
    ranked = [
        score_provider(provider, task)
        for provider in available_providers()
    ]

    return sorted(
        ranked,
        key=lambda item: item.score,
        reverse=True,
    )
