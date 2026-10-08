from __future__ import annotations

from .models import AgentSpec


SPECIALTIES = (
    "planner",
    "researcher",
    "critic",
    "systems-architect",
    "coder",
    "tester",
    "security-reviewer",
    "data-analyst",
    "operations",
    "synthesizer",
)


def build_registry(agent_count: int = 100) -> tuple[AgentSpec, ...]:
    if not 1 <= agent_count <= 100:
        raise ValueError("agent_count must be between 1 and 100")

    agents: list[AgentSpec] = []
    for index in range(agent_count):
        specialty = SPECIALTIES[index % len(SPECIALTIES)]
        number = index + 1
        agents.append(
            AgentSpec(
                id=f"shaggoth-{number:03d}",
                name=f"Shaggoth-{number:03d}",
                specialty=specialty,
                capabilities=frozenset({"reason", "summarize", "classify", "plan"}),
            )
        )
    return tuple(agents)
