from __future__ import annotations

from dataclasses import asdict

from .adapters import MockAdapter, ModelAdapter, OpenAICompatibleAdapter
from .broker import CapabilityBroker
from .config import SwarmConfig
from .models import AgentResult, SwarmReport, SwarmTask, TaskState, utc_now
from .policy import CapabilityPolicy
from .registry import build_registry


class SwarmOrchestrator:
    def __init__(
        self,
        config: SwarmConfig | None = None,
        adapter: ModelAdapter | None = None,
        policy: CapabilityPolicy | None = None,
        broker: CapabilityBroker | None = None,
    ) -> None:
        self.config = config or SwarmConfig()
        self.agents = build_registry(self.config.agent_count)
        self.policy = policy or CapabilityPolicy.from_env()
        self.broker = broker or CapabilityBroker(self.policy)
        self.adapter = adapter or self._build_adapter()

    def _build_adapter(self) -> ModelAdapter:
        if self.config.adapter == "mock":
            return MockAdapter()
        return OpenAICompatibleAdapter(
            base_url=self.config.base_url,
            model=self.config.model,
        )

    def plan(self, goal: str, fanout: int | None = None) -> list[SwarmTask]:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal cannot be empty")

        count = min(fanout or min(8, self.config.agent_count), self.config.max_fanout)
        tasks: list[SwarmTask] = []
        for i in range(count):
            agent = self.agents[i]
            tasks.append(
                SwarmTask(
                    prompt=(
                        f"Goal: {goal}\n"
                        f"Workstream {i + 1}/{count}. Analyze the goal from the perspective of "
                        f"a {agent.specialty}. Return concise findings, risks, and next actions."
                    ),
                    assigned_agent=agent.id,
                    required_capabilities=frozenset({"reason", "plan"}),
                )
            )
        return tasks

    def run(self, goal: str, fanout: int | None = None) -> SwarmReport:
        started_at = utc_now()
        tasks = self.plan(goal, fanout=fanout)
        agents_by_id = {agent.id: agent for agent in self.agents}
        results: list[AgentResult] = []

        for task in tasks:
            agent = agents_by_id[task.assigned_agent]
            ok, missing = self.policy.check(task.required_capabilities)
            if not ok:
                task.state = TaskState.BLOCKED
                results.append(
                    AgentResult(
                        task_id=task.id,
                        agent_id=agent.id,
                        content="",
                        state=TaskState.BLOCKED,
                        error=f"capabilities denied: {', '.join(sorted(missing))}",
                    )
                )
                continue

            task.state = TaskState.RUNNING
            try:
                content = self.adapter.complete(agent, task)
                task.state = TaskState.SUCCEEDED
                results.append(
                    AgentResult(
                        task_id=task.id,
                        agent_id=agent.id,
                        content=content,
                        state=TaskState.SUCCEEDED,
                    )
                )
            except Exception as exc:
                task.state = TaskState.FAILED
                results.append(
                    AgentResult(
                        task_id=task.id,
                        agent_id=agent.id,
                        content="",
                        state=TaskState.FAILED,
                        error=str(exc),
                    )
                )

        summary = self._summarize(goal, results)
        return SwarmReport(goal=goal, results=results, summary=summary, started_at=started_at)

    @staticmethod
    def _summarize(goal: str, results: list[AgentResult]) -> str:
        succeeded = [r for r in results if r.state == TaskState.SUCCEEDED]
        blocked = [r for r in results if r.state == TaskState.BLOCKED]
        failed = [r for r in results if r.state == TaskState.FAILED]
        digest = "\n".join(f"- {r.agent_id}: {r.content}" for r in succeeded)
        return (
            f"Goal: {goal}\n"
            f"Succeeded: {len(succeeded)} | Blocked: {len(blocked)} | Failed: {len(failed)}\n"
            f"Agent findings:\n{digest if digest else '- none'}"
        )

    @staticmethod
    def report_as_dict(report: SwarmReport) -> dict:
        return asdict(report)
