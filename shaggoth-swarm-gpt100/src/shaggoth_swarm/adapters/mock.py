from __future__ import annotations

from .base import ModelAdapter
from ..models import AgentSpec, SwarmTask


class MockAdapter(ModelAdapter):
    def complete(self, agent: AgentSpec, task: SwarmTask) -> str:
        return f"[{agent.name}/{agent.specialty}] Analyzed task {task.id[:8]}: {task.prompt.strip()}"
