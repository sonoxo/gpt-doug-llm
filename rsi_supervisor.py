#!/usr/bin/env python3
"""Bounded, evaluation-gated recursive improvement for the local ZYRA agent.

Candidate edits stay in the working tree for human review; this module never
pushes, merges, deploys, or grants the coding agent additional capabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ai_killswitch import require_ai_allowed
from zyra_agent import MissionBudget, ZyraAgent

MAX_CYCLES = 3


@dataclass(frozen=True)
class Metrics:
    quality: float
    regressions: int
    security_ok: bool

    @classmethod
    def from_json(cls, obj: Any) -> "Metrics":
        if not isinstance(obj, dict) or set(obj) != {"quality", "regressions", "security_ok"}:
            raise ValueError("benchmark must provide quality, regressions, security_ok")
        quality, regressions, security_ok = (obj[key] for key in ("quality", "regressions", "security_ok"))
        if isinstance(quality, bool) or not isinstance(quality, (int, float)):
            raise ValueError("quality must be a number between 0 and 1")
        if not math.isfinite(quality) or not 0.0 <= quality <= 1.0:
            raise ValueError("quality must be a finite number between 0 and 1")
        if isinstance(regressions, bool) or not isinstance(regressions, int) or regressions < 0:
            raise ValueError("regressions must be a nonnegative integer")
        if not isinstance(security_ok, bool):
            raise ValueError("security_ok must be a boolean")
        return cls(float(quality), regressions, security_ok)

    def to_dict(self) -> dict[str, Any]:
        return {"quality": self.quality, "regressions": self.regressions, "security_ok": self.security_ok}


def measured_gain(baseline: Metrics, candidate: Metrics, min_gain: float) -> tuple[bool, str]:
    """Only independent, non-regressing measurements can justify the next round."""
    if not candidate.security_ok or candidate.regressions > baseline.regressions:
        return False, "security or regression gate failed"
    if candidate.regressions > 0:
        return False, "candidate still has known regressions"
    if candidate.quality - baseline.quality < min_gain - 1e-12:
        return False, "quality gain below required minimum"
    return True, "independent benchmark improved without regressions"


class ExternalBenchmark:
    """Runs one fixed operator-supplied Python evaluator outside the editable repo."""

    def __init__(self, script: Path, repo: Path, *, timeout: int = 120):
        self.repo = repo.resolve()
        self.script = script.resolve(strict=True)
        if not self.script.is_file() or self.script.suffix != ".py":
            raise ValueError("benchmark must be a Python file")
        if self.script == self.repo or self.repo in self.script.parents:
            raise ValueError("benchmark must live outside the agent-editable repository")
        self.timeout = timeout
        self.digest = self._digest()

    def _digest(self) -> str:
        return hashlib.sha256(self.script.read_bytes()).hexdigest()

    def __call__(self) -> Metrics:
        if self._digest() != self.digest:
            raise ValueError("trusted benchmark changed during the cycle")
        proc = subprocess.run(
            [sys.executable, str(self.script), str(self.repo)],
            cwd=self.repo,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise ValueError(f"benchmark failed (exit {proc.returncode}): {proc.stderr[-500:]}")
        try:
            metrics = Metrics.from_json(json.loads(proc.stdout))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("benchmark output is not valid quality evidence") from exc
        if self._digest() != self.digest:
            raise ValueError("trusted benchmark changed during execution")
        return metrics


class RecursiveImprovement:
    """Finite sequence: propose -> verify -> independently measure -> retain/rollback."""

    def __init__(
        self,
        agent: ZyraAgent,
        *,
        cycles: int = 1,
        benchmark: Callable[[], Metrics] | None = None,
        min_gain: float = 0.01,
    ):
        if not 1 <= cycles <= MAX_CYCLES:
            raise ValueError(f"cycles must be between 1 and {MAX_CYCLES}")
        if not math.isfinite(min_gain) or not 0.0 < min_gain <= 1:
            raise ValueError("min_gain must be finite and between 0 and 1")
        self.agent = agent
        self.cycles = cycles
        self.benchmark = benchmark
        self.min_gain = min_gain

    def _checks(self, touched: list[str]) -> list[dict[str, Any]]:
        python_files = [path for path in touched if path.endswith(".py")]
        checks = [
            self.agent._tool_run_check("unit", touched),
            self.agent._tool_run_check("ruff", python_files or ["agents"]),
            {"check": "whitespace", **self.agent._run_process(["git", "diff", "--check"], timeout=30)},
        ]
        for expected, check in zip(("unit", "ruff", "whitespace"), checks):
            check.setdefault("check", expected)
        return checks

    def run(self, goal: str) -> dict[str, Any]:
        if not goal.strip():
            raise ValueError("goal is required")
        evidence: dict[str, Any] = {
            "goal": goal,
            "max_cycles": self.cycles,
            "benchmark_required_for_measured_gain": True,
            "promotion": "never automatic",
            "status": "BLOCKED",
            "cycles": [],
        }
        baseline: Metrics | None = None
        if self.benchmark is not None:
            baseline = self.benchmark()  # Fail before mutating if evaluator is invalid.
            evidence["baseline"] = baseline.to_dict()
        for number in range(1, self.cycles + 1):
            require_ai_allowed("RSI mission start")
            objective = f"{goal}\nRSI generation {number}: make one minimal, testable improvement. Do not modify evaluation infrastructure."
            mission = self.agent.run(objective, evolve=True)
            record: dict[str, Any] = {
                "generation": number,
                "mission_id": mission.mission_id,
                "agent_status": mission.status,
                "changed_files": list(mission.touched_files),
                "agent_checks": mission.checks,
                "rolled_back": mission.rolled_back,
            }
            evidence["cycles"].append(record)
            if mission.status != "PASS" or mission.rolled_back:
                record["decision"] = "BLOCKED_AGENT_FAILURE"
                if mission.touched_files and not mission.rolled_back:
                    rollback = self.agent.rollback(mission.mission_id)
                    record["rolled_back"] = bool(rollback.get("rolled_back"))
                evidence["status"] = "BLOCKED"
                break
            if not mission.touched_files or not any(
                check.get("check") == "syntax" and check.get("ok") for check in mission.checks
            ):
                record["decision"] = "REJECT_NO_VERIFIED_CHANGE"
                rollback = self.agent.rollback(mission.mission_id)
                record["rolled_back"] = rollback.get("rolled_back", False)
                evidence["status"] = "BLOCKED"
                break
            try:
                checks = self._checks(mission.touched_files)
                record["independent_checks"] = checks
                if not all(check.get("ok") for check in checks):
                    raise ValueError("one or more independent verification gates failed")
                if self.benchmark is None:
                    record["decision"] = "REVIEW_REQUIRED_UNMEASURED"
                    evidence["status"] = "REVIEW_REQUIRED"
                    break  # Never recursively compound unmeasured changes.
                candidate = self.benchmark()
                record["candidate"] = candidate.to_dict()
                assert baseline is not None
                accepted, reason = measured_gain(baseline, candidate, self.min_gain)
                record["reason"] = reason
                if not accepted:
                    raise ValueError(reason)
                record["decision"] = "MEASURED_GAIN_REVIEW_REQUIRED"
                evidence["status"] = "MEASURED_GAIN_REVIEW_REQUIRED"
                baseline = candidate
                # Verified local candidates may form the basis of the next bounded generation.
            except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                record["decision"] = "REJECT_VERIFICATION_FAILED"
                record["error"] = str(exc)
                rollback = self.agent.rollback(mission.mission_id)
                record["rolled_back"] = bool(rollback.get("rolled_back"))
                evidence["status"] = "BLOCKED"
                break
        return evidence


def require_clean_git_repo(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("repository path is not a directory")
    top = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if top.returncode or Path(top.stdout.strip()).resolve() != root:
        raise ValueError("--repo must be a git working-tree root")
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if dirty.returncode or dirty.stdout.strip():
        raise ValueError("start from a clean git working tree to protect existing changes")
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded local recursive-improvement candidate runner")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--benchmark", help="independent Python evaluator outside the repository")
    parser.add_argument("--min-gain", type=float, default=0.01)
    parser.add_argument("--report", help="local JSON evidence path (must be outside repository)")
    args = parser.parse_args(argv)
    try:
        root = require_clean_git_repo(args.repo)
        benchmark = ExternalBenchmark(Path(args.benchmark), root) if args.benchmark else None
        if args.cycles > 1 and benchmark is None:
            raise ValueError("multiple cycles require an independent benchmark")
        state = Path.home() / ".gpt-doug" / "rsi"
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
        report_path = Path(args.report).expanduser().resolve() if args.report else state / "report.json"
        if report_path == root or root in report_path.parents:
            raise ValueError("report must be outside the repository")
        supervisor = RecursiveImprovement(
            ZyraAgent(root, model=args.model, base_url=args.base_url, budget=MissionBudget()),
            cycles=args.cycles, benchmark=benchmark, min_gain=args.min_gain,
        )
        report = supervisor.run(args.goal)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report_path.chmod(0o600)
        print(json.dumps({"status": report["status"], "report": str(report_path), "cycles": report["cycles"]}, indent=2))
        return 0 if report["status"] in ("REVIEW_REQUIRED", "MEASURED_GAIN_REVIEW_REQUIRED") else 1
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"RSI BLOCKED: {exc}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
