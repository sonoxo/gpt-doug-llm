"""GPT-Doug Universal Council: a bounded, provenance-aware research orchestrator.

This composes existing Stark, Ironman, Orca, Chaos and GPT-Doug-MLM interfaces.
The 'biochip' is a deterministic synthetic neural simulation, not biological
hardware. RSI means evaluation of proposed improvements against supplied test
metrics; it never mutates code, models, tools, infrastructure or permissions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from ai_killswitch import require_ai_allowed
from agents.stark_ironman import Evidence as StarkEvidence
from agents.stark_ironman import IronmanRuntime, StarkPlanner

MAX_GOAL_CHARS = 4000
MAX_EVIDENCE = 16
MAX_CANDIDATES = 8
MAX_NEURONS = 64
MAX_CYCLES = 8
MAX_REVIEWS = 4
MAX_RSI_ROUNDS = 3
MAX_REVIEW_CHARS = 3000


def _digest(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"invalid metric: {name}") from error
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return number


@dataclass(frozen=True)
class Metrics:
    """Measured (not model-predicted) values supplied by a trusted evaluator."""

    quality: float
    safety: float
    efficiency: float

    def validate(self) -> None:
        for name in ("quality", "safety", "efficiency"):
            _finite(getattr(self, name), name)

    def utility(self) -> float:
        self.validate()
        return round(0.5 * self.quality + 0.35 * self.safety + 0.15 * self.efficiency, 5)


@dataclass(frozen=True)
class ImprovementCandidate:
    candidate_id: str
    description: str
    measured: Metrics
    tests_passed: bool
    source_ids: tuple[str, ...]
    permission_change: bool = False
    evaluation_ref: str = ""


class BoundedRSI:
    """Evaluate suggestions only; never execute, retrain, self-copy or deploy."""

    def __init__(self, max_candidates: int = MAX_CANDIDATES) -> None:
        if not 1 <= max_candidates <= MAX_CANDIDATES:
            raise ValueError("max_candidates must be 1..8")
        self.max_candidates = max_candidates

    def evaluate(
        self,
        *,
        baseline: Metrics,
        proposals: Sequence[ImprovementCandidate],
        known_source_ids: set[str],
    ) -> dict[str, Any]:
        require_ai_allowed("bounded RSI evaluation")
        baseline.validate()
        if len(proposals) > self.max_candidates:
            raise ValueError("too many candidates")
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for candidate in proposals:
            require_ai_allowed("bounded RSI candidate evaluation")
            if not isinstance(candidate, ImprovementCandidate):
                raise TypeError("expected ImprovementCandidate")
            cid = candidate.candidate_id
            if not cid or len(cid) > 80 or cid in seen:
                raise ValueError("invalid or duplicate candidate_id")
            seen.add(cid)
            if not candidate.description.strip() or len(candidate.description) > 2000:
                raise ValueError("candidate description missing or too long")
            if not isinstance(candidate.tests_passed, bool) or not isinstance(candidate.permission_change, bool):
                raise ValueError("invalid candidate controls")
            candidate.measured.validate()
            refs = set(candidate.source_ids)
            if len(refs) != len(candidate.source_ids) or any(not ref for ref in refs):
                raise ValueError("invalid source references")
            evaluated = bool(candidate.evaluation_ref.strip()) and candidate.evaluation_ref in known_source_ids
            source_valid = bool(refs) and refs.issubset(known_source_ids)
            gain = round(candidate.measured.utility() - baseline.utility(), 5)
            reasons: list[str] = []
            if not source_valid:
                reasons.append("unverified_provenance")
            if not evaluated:
                reasons.append("missing_evaluation_evidence")
            if not candidate.tests_passed:
                reasons.append("tests_not_passing")
            if candidate.permission_change:
                reasons.append("permission_expansion_forbidden")
            if candidate.measured.safety < baseline.safety:
                reasons.append("safety_regression")
            if gain <= 0:
                reasons.append("no_measured_utility_gain")
            rows.append({
                "candidate_id": cid,
                "measured_delta": gain,
                "status": "eligible_for_human_review" if not reasons else "blocked",
                "reasons": reasons,
                "evidence_ids": sorted(refs),
                "evaluation_ref": candidate.evaluation_ref,
                "executed": False,
            })
        return {
            "mode": "proposal_evaluation_only",
            "baseline_utility": baseline.utility(),
            "candidate_count": len(rows),
            "candidates": rows,
            "auto_mutation": False,
            "auto_merge": False,
            "model_training": False,
            "human_approval_required": True,
        }

    def evaluate_rounds(
        self, *, baseline: Metrics,
        rounds: Sequence[Sequence[ImprovementCandidate]],
        known_source_ids: set[str],
    ) -> dict[str, Any]:
        """Bounded multi-round evaluation; baseline never silently changes."""
        require_ai_allowed("bounded RSI round start")
        if not 1 <= len(rounds) <= MAX_RSI_ROUNDS:
            raise ValueError("RSI rounds must be between 1 and 3")
        results = []
        best_candidate = None
        best_gain = 0.0
        all_ids: set[str] = set()
        for index, candidates in enumerate(rounds, start=1):
            require_ai_allowed("bounded RSI round evaluation")
            if any(c.candidate_id in all_ids for c in candidates):
                raise ValueError("candidate IDs must be unique across rounds")
            all_ids.update(c.candidate_id for c in candidates)
            result = self.evaluate(baseline=baseline, proposals=candidates,
                                   known_source_ids=known_source_ids)
            results.append({"round": index, **result})
            for entry in result["candidates"]:
                if entry["status"] == "eligible_for_human_review" and entry["measured_delta"] > best_gain:
                    best_candidate = entry["candidate_id"]
                    best_gain = entry["measured_delta"]
        return {
            "mode": "bounded_multi_round_proposal_evaluation",
            "round_count": len(results),
            "rounds": results,
            "top_candidate_for_review": best_candidate,
            "baseline_unchanged": True,
            "auto_mutation": False,
            "auto_merge": False,
            "human_approval_required": True,
        }


def simulate_biochip(
    *, goal: str, neurons: int = 12, cycles: int = 3,
    graph_factory: Optional[Callable[[int], Any]] = None,
) -> dict[str, Any]:
    """Drive an isolated, finite synthetic neuron graph; no actuators or wetware."""
    require_ai_allowed("synthetic biochip simulation")
    if not 2 <= neurons <= MAX_NEURONS or not 1 <= cycles <= MAX_CYCLES:
        raise ValueError("neuron count (2..64) or cycles (1..8) outside bound")
    if graph_factory is None:
        from research_lab.orca_neurocloud import NeuroGraph
        graph_factory = NeuroGraph
    graph = graph_factory(neurons)
    seed = hashlib.sha256(goal.encode("utf-8")).digest()
    result = []
    for tick in range(cycles):
        require_ai_allowed("synthetic biochip tick")
        stimuli = [round(((seed[(i + tick) % len(seed)] / 255.0) - 0.5) * 0.5, 6)
                   for i in range(neurons)]
        result = list(graph.tick(stimuli))
        if len(result) != neurons or any(not math.isfinite(float(v)) or abs(float(v)) > 1.0 for v in result):
            raise ValueError("neuron backend returned invalid state")
    state = [round(float(v), 6) for v in result]
    return {
        "kind": "synthetic_neuron_simulation",
        "biological_hardware": False,
        "physical_actuation": False,
        "network_access": False,
        "neurons": neurons,
        "cycles": cycles,
        "final_state": state,
        "state_sha256": _digest(state),
    }


class UniversalCouncil:
    """Collaborative, bounded AI planning with independently gated components."""

    AGENTS = ("gpt-doug-llm", "gpt-stark-llm", "gpt-ironman-llm",
              "gpt-orca-llm", "gpt-chaos", "gpt-doug-mlm")

    def __init__(
        self, *,
        planner: Optional[StarkPlanner] = None,
        ironman: Optional[IronmanRuntime] = None,
        orca_backend: Optional[Callable[..., Mapping[str, Any]]] = None,
        provider_registry: Optional[Any] = None,
        graph_factory: Optional[Callable[[int], Any]] = None,
    ) -> None:
        self.planner = planner or StarkPlanner()
        self.ironman = ironman or IronmanRuntime()
        self.orca_backend = orca_backend
        self.providers = provider_registry
        self.graph_factory = graph_factory

    @staticmethod
    def _normalize_evidence(evidence: Sequence[StarkEvidence]) -> tuple[StarkEvidence, ...]:
        if len(evidence) > MAX_EVIDENCE:
            raise ValueError("too much evidence")
        unique: set[str] = set()
        cleaned = []
        for item in evidence:
            if not isinstance(item, StarkEvidence):
                raise TypeError("evidence must be Stark Evidence objects")
            if item.source_id in unique:
                raise ValueError("duplicate source IDs")
            unique.add(item.source_id)
            cleaned.append(item)
        return tuple(cleaned)

    @staticmethod
    def _chaos_review(plan: Mapping[str, Any], sources: set[str]) -> dict[str, Any]:
        """Policy checks derived from the Chaos adversarial-evaluation worker role."""
        steps = plan["graph"]["steps"]
        unknowns = [ref for step in steps for ref in step.get("source_ids", []) if ref not in sources]
        fabric = ["simulation", "alternate-strategy", "stress-test", "adversarial-evaluation", "verification"]
        try:
            from gpt_chaos.runtime import GPTChaos
            fabric = list(GPTChaos.WORKER_FABRIC)
        except ImportError:
            pass  # Does not invent a completed Chaos runtime job.
        return {
            "agent": "gpt-chaos",
            "mode": "static_adversarial_checks",
            "worker_fabric": fabric,
            "unknown_sources": sorted(set(unknowns)),
            "passes_structure": len(steps) <= 6 and not unknowns,
            "external_stress_test_executed": False,
        }

    def _orca(self, goal: str, evidence: tuple[StarkEvidence, ...], live: bool) -> dict[str, Any]:
        if not live:
            return {"agent": "gpt-orca-llm", "status": "opt_in_not_run", "model_called": False}
        require_ai_allowed("Orca council model invocation")
        from agents.adaptive_intelligence import Evidence as OrcaEvidence
        from agents.gpt_orca_llm import OrcaCouncil
        rows = [OrcaEvidence(source_id=e.source_id, text=e.statement,
                             provenance=e.provenance) for e in evidence]
        council = OrcaCouncil(backend=self.orca_backend) if self.orca_backend else OrcaCouncil()
        result = council.run(goal, rows)
        return {
            "agent": "gpt-orca-llm",
            "status": "completed" if result.completed else "failed",
            "model_called": True,
            "evidence_ids": result.evidence_ids,
            "roles": [{"role": t.role, "error": t.error,
                       "output": t.output[:MAX_REVIEW_CHARS]} for t in result.turns],
            "answer": result.answer[:MAX_REVIEW_CHARS],
            "outputs_are_unverified": True,
        }

    def _mlm(self, plan: Mapping[str, Any], providers: Sequence[str]) -> dict[str, Any]:
        if len(providers) > MAX_REVIEWS or len(set(providers)) != len(providers):
            raise ValueError("invalid model reviewer selection")
        if not providers:
            return {"agent": "gpt-doug-mlm", "status": "opt_in_not_run", "reviews": []}
        if self.providers is None:
            raise ValueError("model reviewers require an explicit provider registry")
        packet = json.dumps({"goal": plan["graph"]["task"],
                             "steps": plan["graph"]["steps"]}, ensure_ascii=False)
        reviews = []
        for name in providers:
            require_ai_allowed("MLM registered reviewer")
            try:
                answer = str(self.providers.get(name).review(packet))
                reviews.append({"provider": name, "status": "proposed",
                                "text": answer[:MAX_REVIEW_CHARS], "verified": False})
            except Exception as error:
                reviews.append({"provider": name, "status": "failed",
                                "error_type": type(error).__name__, "verified": False})
        return {"agent": "gpt-doug-mlm", "status": "completed", "reviews": reviews}

    def run(
        self, goal: str, *,
        evidence: Sequence[StarkEvidence] = (),
        baseline: Metrics = Metrics(0.5, 0.5, 0.5),
        improvement_candidates: Sequence[ImprovementCandidate] = (),
        improvement_rounds: Sequence[Sequence[ImprovementCandidate]] = (),
        neurons: int = 12,
        cycles: int = 3,
        live_orca: bool = False,
        mlm_reviewers: Sequence[str] = (),
    ) -> dict[str, Any]:
        require_ai_allowed("Universal Council start")
        if not isinstance(goal, str) or not goal.strip() or len(goal) > MAX_GOAL_CHARS:
            raise ValueError("goal must be nonempty and <= 4000 characters")
        rows = self._normalize_evidence(evidence)
        normalized_goal = goal.strip()
        plan = self.planner.plan(normalized_goal, constraints=(
            "read-only planning and simulation by default",
            "source-provenance required; do not invent successful execution",
            "external deployment and model updates require separate human approval",
        ), evidence=rows)
        source_ids = {row.source_id for row in rows}
        require_ai_allowed("Universal Council review")
        chaos = self._chaos_review(plan, source_ids)
        orca = self._orca(normalized_goal, rows, live_orca)
        mlm = self._mlm(plan, mlm_reviewers)
        require_ai_allowed("Universal Council simulation")
        neuro = simulate_biochip(goal=normalized_goal, neurons=neurons, cycles=cycles,
                                graph_factory=self.graph_factory)
        if improvement_candidates and improvement_rounds:
            raise ValueError("use either candidates or rounds, not both")
        lab = BoundedRSI()
        improvement = (
            lab.evaluate_rounds(baseline=baseline, rounds=improvement_rounds,
                                known_source_ids=source_ids)
            if improvement_rounds else
            lab.evaluate(baseline=baseline, proposals=improvement_candidates,
                         known_source_ids=source_ids)
        )
        # No action mappings are accepted here; Ironman cannot reach external tools.
        staged = self.ironman.execute(plan)
        report = {
            "schema": "gpt-doug.universal-council.v1",
            "goal": normalized_goal,
            "agents": list(self.AGENTS),
            "source_ids": sorted(source_ids),
            "stark": plan,
            "ironman": staged,
            "orca": orca,
            "chaos": chaos,
            "mlm": mlm,
            "synthetic_biochip": neuro,
            "bounded_rsi": improvement,
            "permissions": {
                "automated_code_changes": False,
                "self_replication": False,
                "external_tool_execution": False,
                "hardware_control": False,
                "human_approval_required": True,
            },
            "claim": "bounded research software, not artificial superintelligence or physical biochip",
        }
        report["report_sha256"] = _digest(report)
        require_ai_allowed("Universal Council completed")
        return report


def _read_json(path: str) -> Any:
    filename = Path(path)
    if filename.is_symlink() or not filename.is_file() or filename.stat().st_size > 65536:
        raise ValueError("input must be a small, regular, non-symlink JSON file")
    return json.loads(filename.read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="gpt-universal-council", description=__doc__)
    parser.add_argument("goal")
    parser.add_argument("--evidence-json", help="JSON array of source_id, statement, provenance")
    parser.add_argument("--neurons", type=int, default=12)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--live-orca", action="store_true", help="opt into configured GPT-Orca model inference")
    args = parser.parse_args(argv)
    try:
        supplied = _read_json(args.evidence_json) if args.evidence_json else []
        if not isinstance(supplied, list):
            raise ValueError("evidence JSON must be an array")
        source_rows = [StarkEvidence(**item) for item in supplied]
        result = UniversalCouncil().run(args.goal, evidence=source_rows,
                                        neurons=args.neurons, cycles=args.cycles,
                                        live_orca=args.live_orca)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if result["orca"]["status"] != "failed" else 1
    except (OSError, ValueError, TypeError, PermissionError, RuntimeError) as error:
        print(json.dumps({"ok": False, "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())