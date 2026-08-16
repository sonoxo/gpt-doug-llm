from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .classifier import classify
from .planner import make_plan
from .verifier import verify_text


@dataclass
class Iteration:
    number: int
    draft: str
    score: float
    problems: list[str] = field(default_factory=list)


@dataclass
class IterationResult:
    answer: str
    score: float
    iterations: list[Iteration]
    plan: list[str]


class DougIterator:
    def __init__(
        self,
        max_iterations: int = 3,
        target_score: float = 0.95,
    ):
        self.max_iterations = max_iterations
        self.target_score = target_score

    def system_prompt(self, prompt: str) -> str:
        task = classify(prompt)

        return f"""
You are GPT Doug.

TASK TYPE:
{task.task_type}

COMPLEXITY:
{task.complexity:.2f}

METHOD:
1. Understand the objective.
2. Preserve existing work.
3. Inspect before modifying.
4. Prefer executable solutions.
5. Verify assumptions.
6. Test code changes.
7. Detect contradictions.
8. Revise weak solutions.
9. Report failures clearly.

NO-OLLAMA POLICY:
Do not require Ollama.
Do not use localhost:11434.
Do not download local model weights automatically.

Return the strongest supported answer.
""".strip()

    def run(
        self,
        prompt: str,
        generate: Callable[[str, str], str],
    ) -> IterationResult:

        task = classify(prompt)
        plan = make_plan(task)
        system = self.system_prompt(prompt)

        attempts: list[Iteration] = []
        previous = ""

        for number in range(
            1,
            self.max_iterations + 1,
        ):

            if number == 1:
                user_prompt = prompt
            else:
                user_prompt = f"""
ORIGINAL REQUEST:
{prompt}

PREVIOUS ANSWER:
{previous}

PROBLEMS:
{attempts[-1].problems}

Produce an improved answer.
Fix the detected weaknesses.
Do not merely rephrase.
""".strip()

            draft = generate(
                system,
                user_prompt,
            )

            verification = verify_text(
                prompt,
                draft,
            )

            attempt = Iteration(
                number=number,
                draft=draft,
                score=verification.score,
                problems=verification.problems,
            )

            attempts.append(attempt)
            previous = draft

            if (
                verification.score
                >= self.target_score
            ):
                break

        best = max(
            attempts,
            key=lambda item: item.score,
        )

        return IterationResult(
            answer=best.draft,
            score=best.score,
            iterations=attempts,
            plan=plan,
        )
