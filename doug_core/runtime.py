from __future__ import annotations

from .classifier import classify
from .memory import Memory
from .planner import make_plan
from .reasoner import reason
from .router import route
from .types import DougResult
from .verifier import verify_text


class DougRuntime:
    def __init__(self):
        self.memory = Memory()

    def analyze(
        self,
        prompt: str,
    ) -> dict:

        task = classify(prompt)
        routing = route(task)
        plan = make_plan(task)
        reasoning = reason(prompt)

        return {
            "task": task,
            "routing": routing,
            "plan": plan,
            "reasoning": reasoning,
        }

    def offline_response(
        self,
        prompt: str,
    ) -> DougResult:

        analysis = self.analyze(prompt)

        best = analysis["routing"][0]

        answer = (
            "GPT Doug is operating in local orchestration mode. "
            "Project inspection, planning, routing, memory, "
            "verification, release analysis, defensive security "
            "inspection and workspace tools remain available "
            "without an AI provider."
        )

        verification = verify_text(
            prompt,
            answer,
        )

        self.memory.add(
            "interaction",
            prompt,
            {
                "provider": best.name,
                "task_type": (
                    analysis["task"].task_type
                ),
                "verification": (
                    verification.score
                ),
            },
        )

        return DougResult(
            answer=answer,
            provider=best.name,
            confidence=verification.score,
            steps=analysis["plan"],
            metadata={
                "routing": [
                    {
                        "provider": item.name,
                        "score": item.score,
                        "reason": item.reason,
                    }
                    for item
                    in analysis["routing"]
                ]
            },
        )
