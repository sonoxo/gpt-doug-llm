"""A bounded logical-agent swarm scheduler.

Agent identities are metadata, not running processes. This core deliberately avoids
spawning agents, making network calls, or executing submitted task content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Callable, Iterable


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    role: str
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task:
    task_id: str
    objective: str
    required_capabilities: tuple[str, ...] = ()
    risk: str = "low"


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    assigned_agent_id: str | None
    status: str
    reason: str


@dataclass
class SwarmBrain:
    """Registry + deterministic, bounded dispatcher for logical agents."""
    logical_agent_count: int = 99_999_999_999
    max_active_workers: int = 8
    agents: dict[str, AgentSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.logical_agent_count < 1:
            raise ValueError("logical_agent_count must be positive")
        if not 1 <= self.max_active_workers <= 256:
            raise ValueError("max_active_workers must be between 1 and 256")

    def virtual_agent_id(self, index: int, role: str = "general") -> str:
        """Stable virtual identity without materializing billions of objects."""
        if not 0 <= index < self.logical_agent_count:
            raise IndexError("virtual agent index out of range")
        digest = sha256(f"sonoxo:gpt-doug:{index}:{role}".encode()).hexdigest()[:16]
        return f"agent:{index}:{digest}"

    def register_worker(self, agent: AgentSpec) -> None:
        if not agent.agent_id.strip() or not agent.role.strip():
            raise ValueError("agent_id and role are required")
        self.agents[agent.agent_id] = agent

    def dispatch(self, task: Task, *, policy_approved: bool = False) -> TaskResult:
        """Choose a registered worker; fail closed for risky or unapproved tasks."""
        if not task.task_id.strip() or not task.objective.strip():
            return TaskResult(task.task_id, None, "held", "task_id_or_objective_missing")
        if task.risk.lower() not in {"low", "medium", "high", "critical"}:
            return TaskResult(task.task_id, None, "held", "unknown_risk_level")
        if task.risk.lower() in {"high", "critical"} and not policy_approved:
            return TaskResult(task.task_id, None, "held", "policy_approval_required")
        eligible = [
            agent for agent in self.agents.values()
            if set(task.required_capabilities).issubset(set(agent.capabilities))
        ]
        if not eligible:
            return TaskResult(task.task_id, None, "queued", "no_eligible_registered_worker")
        # Deterministic assignment makes runs reproducible and easy to audit.
        eligible.sort(key=lambda item: item.agent_id)
        slot = int(sha256(task.task_id.encode()).hexdigest(), 16) % len(eligible)
        return TaskResult(task.task_id, eligible[slot].agent_id, "assigned", "capabilities_match")

    def snapshot(self) -> dict:
        return {
            "logical_agent_count": self.logical_agent_count,
            "logical_id_space_materialized": False,
            "registered_workers": len(self.agents),
            "max_active_workers": self.max_active_workers,
            "external_calls_enabled": False,
            "autonomous_deployment_enabled": False,
            "dispatch_mode": "deterministic_bounded",
        }
