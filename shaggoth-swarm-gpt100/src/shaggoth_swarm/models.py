from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AgentSpec:
    id: str
    name: str
    specialty: str
    capabilities: frozenset[str] = frozenset()


@dataclass(slots=True)
class SwarmTask:
    prompt: str
    assigned_agent: str
    depth: int = 0
    required_capabilities: frozenset[str] = frozenset()
    id: str = field(default_factory=lambda: uuid4().hex)
    state: TaskState = TaskState.PENDING
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class AgentResult:
    task_id: str
    agent_id: str
    content: str
    state: TaskState
    created_at: str = field(default_factory=utc_now)
    error: str | None = None


@dataclass(slots=True)
class SwarmReport:
    goal: str
    results: list[AgentResult]
    summary: str
    started_at: str
    completed_at: str = field(default_factory=utc_now)

    @property
    def succeeded(self) -> int:
        return sum(r.state == TaskState.SUCCEEDED for r in self.results)

    @property
    def blocked(self) -> int:
        return sum(r.state == TaskState.BLOCKED for r in self.results)

    @property
    def failed(self) -> int:
        return sum(r.state == TaskState.FAILED for r in self.results)
