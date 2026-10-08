from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import AgentSpec, SwarmTask


class ModelAdapter(ABC):
    @abstractmethod
    def complete(self, agent: AgentSpec, task: SwarmTask) -> str:
        raise NotImplementedError
