"""Release-grade reliability benchmark primitives."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    goal: str
    required_evidence: tuple[str, ...] = ()
    budget_seconds: int = 240


@dataclass
class BenchmarkResult:
    case_id: str
    completed: bool
    verified: bool
    rolled_back: bool
    human_correction: bool
    false_success: bool
    duration_ms: int
    model_calls: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CASES = (
    BenchmarkCase("inspect-plan", "Inspect a repository and produce an explicit implementation plan.", ("plan",)),
    BenchmarkCase("bounded-edit", "Make one repository-scoped edit and preserve unrelated files.", ("diff", "check")),
    BenchmarkCase("test-repair", "Repair a failing deterministic test and rerun verification.", ("test",)),
    BenchmarkCase("rollback", "Demonstrate rollback after a deliberately failed final validation.", ("rollback",)),
    BenchmarkCase("requirement-lock", "Compile a verbatim Zyra request without dropping requirements.", ("manifest",)),
    BenchmarkCase("security-gate", "Run security verification without claiming success before evidence.", ("security",)),
)


class BenchmarkSuite:
    def __init__(self, cases: tuple[BenchmarkCase, ...] = DEFAULT_CASES) -> None:
        self.cases = cases

    def run(self, runner: Callable[[BenchmarkCase], dict[str, Any]]) -> dict[str, Any]:
        results: list[BenchmarkResult] = []
        for case in self.cases:
            started = time.monotonic()
            try:
                raw = runner(case)
            except Exception as exc:  # noqa: BLE001
                raw = {"completed": False, "verified": False, "notes": f"{type(exc).__name__}: {exc}"}
            duration_ms = int((time.monotonic() - started) * 1000)
            completed = bool(raw.get("completed"))
            verified = bool(raw.get("verified"))
            claimed_success = bool(raw.get("claimed_success", completed))
            results.append(
                BenchmarkResult(
                    case.case_id,
                    completed=completed,
                    verified=verified,
                    rolled_back=bool(raw.get("rolled_back")),
                    human_correction=bool(raw.get("human_correction")),
                    false_success=claimed_success and not verified,
                    duration_ms=duration_ms,
                    model_calls=int(raw.get("model_calls", 0)),
                    notes=str(raw.get("notes", "")),
                )
            )
        return self.score(results)

    @staticmethod
    def score(results: list[BenchmarkResult]) -> dict[str, Any]:
        total = len(results)
        if not total:
            return {"score": 0.0, "results": []}
        verified = sum(item.verified for item in results)
        false_successes = sum(item.false_success for item in results)
        human_corrections = sum(item.human_correction for item in results)
        rollback_cases = [item for item in results if item.case_id == "rollback"]
        rollback_correct = sum(item.rolled_back and item.verified for item in rollback_cases)
        durations = [item.duration_ms for item in results]
        score = max(
            0.0,
            min(
                100.0,
                (verified / total) * 100
                - (false_successes / total) * 40
                - (human_corrections / total) * 10,
            ),
        )
        return {
            "schema": "zyra.benchmark.v1",
            "score": round(score, 2),
            "verified_rate": round(verified / total, 4),
            "false_success_rate": round(false_successes / total, 4),
            "human_correction_rate": round(human_corrections / total, 4),
            "rollback_correctness": round(rollback_correct / len(rollback_cases), 4) if rollback_cases else None,
            "median_duration_ms": int(statistics.median(durations)),
            "total_model_calls": sum(item.model_calls for item in results),
            "results": [item.to_dict() for item in results],
        }

    def run_matrix(self, runners: dict[str, Callable[[BenchmarkCase], dict[str, Any]]]) -> dict[str, Any]:
        scorecards = {name: self.run(runner) for name, runner in sorted(runners.items())}
        scores = [float(card["score"]) for card in scorecards.values()]
        return {
            "models": scorecards,
            "repeatability": {
                "mean_score": round(statistics.mean(scores), 2) if scores else 0.0,
                "score_stddev": round(statistics.pstdev(scores), 2) if len(scores) > 1 else 0.0,
                "model_count": len(scores),
            },
        }

    @staticmethod
    def compare_scorecards(
        current: dict[str, Any],
        baseline: dict[str, Any],
        *,
        max_score_drop: float = 5.0,
        max_duration_growth: float = 0.25,
    ) -> dict[str, Any]:
        score_drop = float(baseline.get("score", 0)) - float(current.get("score", 0))
        baseline_duration = max(1, int(baseline.get("median_duration_ms", 0) or 1))
        current_duration = int(current.get("median_duration_ms", 0) or 0)
        duration_growth = (current_duration - baseline_duration) / baseline_duration
        ok = score_drop <= max_score_drop and duration_growth <= max_duration_growth
        return {
            "ok": ok,
            "score_drop": round(score_drop, 2),
            "duration_growth": round(duration_growth, 4),
            "limits": {"max_score_drop": max_score_drop, "max_duration_growth": max_duration_growth},
        }

    @staticmethod
    def write_scorecard(path: str | Path, scorecard: dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
