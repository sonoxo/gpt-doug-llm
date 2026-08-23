"""Dependency-aware mission DAG with acceptance criteria and checkpoint metadata."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class MissionStep:
    step_id: str
    title: str
    executor: str
    depends_on: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    acceptance: tuple[str, ...] = ()
    checkpoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StepResult:
    step_id: str
    ok: bool
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MissionDAG:
    def __init__(self, steps: list[MissionStep]) -> None:
        self.steps = {step.step_id: step for step in steps}
        if len(self.steps) != len(steps):
            raise ValueError("duplicate step_id")
        self._validate()

    def _validate(self) -> None:
        for step in self.steps.values():
            missing = [dep for dep in step.depends_on if dep not in self.steps]
            if missing:
                raise ValueError(f"{step.step_id} missing dependencies: {missing}")
        self.levels()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MissionDAG":
        steps = []
        for item in payload.get("steps", []):
            steps.append(
                MissionStep(
                    step_id=str(item["step_id"]),
                    title=str(item.get("title", item["step_id"])),
                    executor=str(item.get("executor", "gpt-doug-core")),
                    depends_on=tuple(item.get("depends_on", [])),
                    capabilities=tuple(item.get("capabilities", [])),
                    acceptance=tuple(item.get("acceptance", [])),
                    checkpoint=item.get("checkpoint"),
                )
            )
        return cls(steps)

    def levels(self) -> list[list[MissionStep]]:
        pending = set(self.steps)
        complete: set[str] = set()
        levels: list[list[MissionStep]] = []
        while pending:
            ready_ids = sorted(
                step_id for step_id in pending
                if set(self.steps[step_id].depends_on) <= complete
            )
            if not ready_ids:
                raise ValueError("mission DAG contains a cycle")
            level = [self.steps[step_id] for step_id in ready_ids]
            levels.append(level)
            complete.update(ready_ids)
            pending.difference_update(ready_ids)
        return levels

    def plan(self) -> dict[str, Any]:
        levels = self.levels()
        return {
            "steps": [step.to_dict() for level in levels for step in level],
            "levels": [[step.step_id for step in level] for level in levels],
        }

    def execute(
        self,
        runner: Callable[[MissionStep], StepResult],
        *,
        max_workers: int = 4,
        resume_after: set[str] | None = None,
    ) -> dict[str, StepResult]:
        done = set(resume_after or ())
        results: dict[str, StepResult] = {
            step_id: StepResult(step_id, True, "resumed from checkpoint")
            for step_id in done if step_id in self.steps
        }
        for level in self.levels():
            runnable = [
                step for step in level
                if step.step_id not in done
                and all(results.get(dep, StepResult(dep, False)).ok for dep in step.depends_on)
            ]
            blocked = [step for step in level if step.step_id not in done and step not in runnable]
            for step in blocked:
                results[step.step_id] = StepResult(step.step_id, False, "blocked by failed dependency")
            if not runnable:
                continue
            with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(runnable)))) as pool:
                futures = {}
                for step in runnable:
                    started = time.monotonic()
                    futures[pool.submit(runner, step)] = (step, started)
                for future in as_completed(futures):
                    step, started = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:  # noqa: BLE001
                        result = StepResult(step.step_id, False, f"{type(exc).__name__}: {exc}")
                    result.duration_ms = int((time.monotonic() - started) * 1000)
                    results[step.step_id] = result
        return results

    def acceptance_criteria(self) -> dict[str, list[str]]:
        return {step.step_id: list(step.acceptance) for step in self.steps.values()}
