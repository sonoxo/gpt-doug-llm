from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw in (None, "") else int(raw)


@dataclass(frozen=True, slots=True)
class SwarmConfig:
    agent_count: int = field(default_factory=lambda: _env_int("SHAGGOTH_AGENT_COUNT", 100))
    max_fanout: int = field(default_factory=lambda: _env_int("SHAGGOTH_MAX_FANOUT", 16))
    max_depth: int = field(default_factory=lambda: _env_int("SHAGGOTH_MAX_DEPTH", 2))
    adapter: str = field(default_factory=lambda: os.getenv("SHAGGOTH_ADAPTER", "mock"))
    base_url: str = field(default_factory=lambda: os.getenv("SHAGGOTH_BASE_URL", "https://api.openai.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("SHAGGOTH_MODEL", ""))

    def __post_init__(self) -> None:
        if not 1 <= self.agent_count <= 100:
            raise ValueError("agent_count must be between 1 and 100")
        if not 1 <= self.max_fanout <= self.agent_count:
            raise ValueError("max_fanout must be between 1 and agent_count")
        if not 0 <= self.max_depth <= 8:
            raise ValueError("max_depth must be between 0 and 8")
        if self.adapter not in {"mock", "openai-compatible"}:
            raise ValueError("adapter must be 'mock' or 'openai-compatible'")
