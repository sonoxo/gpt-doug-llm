from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    prompt: str
    task_type: str = "general"
    complexity: float = 0.5
    needs_code: bool = False
    needs_tools: bool = False
    needs_reasoning: bool = True
    needs_security: bool = False
    needs_files: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Candidate:
    name: str
    score: float
    reason: str


@dataclass
class DougResult:
    answer: str
    provider: str
    confidence: float
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
