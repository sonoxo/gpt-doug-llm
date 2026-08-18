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
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if max_iterations > 1000:
            raise ValueError("max_iterations may not exceed 1000")
        self.max_iterations = max_iterations
        self.target_score = target_score

    @classmethod
    def time_jump_1000(cls, target_score: float = 0.995) -> "DougIterator":
        """Create the bounded high-depth refinement profile.

        Time Jump 1000 means *up to* 1000 verified refinement cycles. It is not
        uncontrolled recursive self-modification: every cycle is scored by the
        verifier and the best verified answer is returned.
        """
        return cls(max_iterations=1000, target_score=target_score)

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
10. Preserve safety, provenance, and human control across every refinement cycle.

FRAMEWORK INVARIANTS:
- Never claim a tool or test succeeded without a real execution receipt.
- Never promote unverified knowledge into trusted memory.
- Prefer source-backed facts over generated assumptions.
- Treat security boundaries as fixed constraints during optimization.
- Stop early once the target verification score is achieved.

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

        for number in range(1, self.max_iterations + 1):
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

REFINEMENT CYCLE:
{number}/{self.max_iterations}

Produce an improved answer.
Fix the detected weaknesses.
Do not merely rephrase.
Preserve verified strengths from the best prior attempt.
""".strip()

            draft = generate(system, user_prompt)
            verification = verify_text(prompt, draft)

            attempt = Iteration(
                number=number,
                draft=draft,
                score=verification.score,
                problems=verification.problems,
            )

            attempts.append(attempt)
            previous = draft

            if verification.score >= self.target_score:
                break

        best = max(attempts, key=lambda item: item.score)

        return IterationResult(
            answer=best.draft,
            score=best.score,
            iterations=attempts,
            plan=plan,
        )
