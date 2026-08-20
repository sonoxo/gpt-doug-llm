from __future__ import annotations

from .classifier import classify
from .core_profile import get_core_profile
from .memory import Memory
from .planner import make_plan
from .reasoner import reason
from .router import route
from .types import DougResult
from .verifier import verify_text


class DougRuntime:
    def __init__(self):
        self.memory = Memory()
        self.core_profile = get_core_profile()

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
            "core_profile": self.core_profile,
        }

    def offline_response(
        self,
        prompt: str,
    ) -> DougResult:

        analysis = self.analyze(prompt)

        best = analysis["routing"][0]

        answer = (
            f"{self.core_profile.name} is operating in local orchestration mode. "
            "Project inspection, planning, routing, memory, verification, "
            "release analysis, defensive security inspection, mission-assurance "
            "analysis, non-weaponized UAV readiness, and workspace tools remain "
            "available without an AI provider. Capability claims use the "
            "PLANNED -> IMPLEMENTED -> TESTED -> VERIFIED truth model."
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
                "core_profile": self.core_profile.name,
                "core_version": self.core_profile.version,
            },
        )

        return DougResult(
            answer=answer,
            provider=best.name,
            confidence=verification.score,
            steps=analysis["plan"],
            metadata={
                "core_profile": self.core_profile.name,
                "core_version": self.core_profile.version,
                "truth_labels": list(self.core_profile.truth_labels),
                "max_same_failure_retries": self.core_profile.max_same_failure_retries,
                "routing": [
                    {
                        "provider": item.name,
                        "score": item.score,
                        "reason": item.reason,
                    }
                    for item
                    in analysis["routing"]
                ],
            },
        )
