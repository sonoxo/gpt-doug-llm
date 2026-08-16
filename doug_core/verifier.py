from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Verification:
    score: float
    problems: list[str]


def verify_text(prompt: str, answer: str) -> Verification:
    problems: list[str] = []

    stripped = answer.strip()

    if not stripped:
        problems.append("empty answer")

    if len(stripped) < 8:
        problems.append("answer suspiciously short")

    lower = answer.lower()

    if "todo" in lower:
        problems.append("unfinished TODO marker")

    if "localhost:11434" in lower:
        problems.append("forbidden Ollama endpoint")

    if "127.0.0.1:11434" in lower:
        problems.append("forbidden Ollama endpoint")

    if "ollama serve" in lower:
        problems.append("attempt to start Ollama")

    score = max(
        0.0,
        1.0 - (0.20 * len(problems)),
    )

    return Verification(
        score=score,
        problems=problems,
    )
