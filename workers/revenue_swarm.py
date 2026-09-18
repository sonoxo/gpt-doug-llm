#!/usr/bin/env python3
"""Bounded, provider-aware revenue swarm for Sonoxo / GPT-Doug.

The swarm parallelizes independent prospect pipelines while keeping each
prospect's stages ordered:

scout -> qualify -> match -> proposal -> outreach_draft -> qa

Important operational rule: this module never sends outreach, moves money, or
performs an irreversible external action. It creates drafts and marks those
actions as approval-required for a human or an authorized connector layer.

Concurrency is intentionally bounded. Remote/cloud providers can use a larger
pool; local Ollama is clamped to a small number of concurrent pipelines to
avoid thrashing a single local model server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "workers" / "live"
RUN_LOG = LIVE_DIR / "revenue-swarm.jsonl"
METRICS_FILE = LIVE_DIR / "revenue-swarm-metrics.json"

FOREVER_RULE = "ForeverRuleGPTDOUGLLMMAXMIMIXK"

STAGES = (
    "scout",
    "qualify",
    "match",
    "proposal",
    "outreach_draft",
    "qa",
)

ROLE_PROMPTS = {
    "scout": (
        "You are the Sonoxo Scout bee. Review the supplied prospect record. "
        "Extract concrete business pain, urgency signals, decision-maker clues, "
        "and evidence gaps. Do not invent facts."
    ),
    "qualify": (
        "You are the Sonoxo Qualification bee. Determine whether the prospect "
        "has a plausible problem, budget signal, and implementation fit for AI "
        "automation services. Separate known facts from assumptions."
    ),
    "match": (
        "You are the Sonoxo Offer-Matching bee. Map the prospect to the best "
        "available offer: AI Deployment Sprint, Sonoxo Pro, Sonoxo Business, "
        "or enterprise quote. Explain the match using only supplied evidence."
    ),
    "proposal": (
        "You are the Sonoxo Proposal bee. Draft a concise value proposition, "
        "scope, expected outcome, and a next step. Do not promise unsupported ROI."
    ),
    "outreach_draft": (
        "You are the Sonoxo Outreach bee. Produce one concise personalized "
        "outreach draft. Do not send it. Do not claim prior contact. Do not use "
        "deceptive urgency. Mark the draft as requiring human approval."
    ),
    "qa": (
        "You are the Sonoxo QA bee. Review the pipeline output for factual "
        "support, duplication, overclaiming, privacy concerns, and whether any "
        "external action still requires approval. Return a short pass/fail review."
    ),
}

DEFAULT_OFFERS = {
    "deployment_sprint": {"name": "Sonoxo AI Deployment Sprint", "price": "$2,500 one-time"},
    "pro": {"name": "Sonoxo Pro", "price": "$99/month"},
    "business": {"name": "Sonoxo Business", "price": "$499/month"},
    "enterprise": {"name": "Sonoxo Enterprise", "price": "custom quote"},
}


@dataclass(frozen=True)
class Prospect:
    prospect_id: str
    name: str = ""
    organization: str = ""
    pain: str = ""
    budget_signal: str = ""
    channel: str = ""
    context: str = ""

    @classmethod
    def from_mapping(cls, value: dict) -> "Prospect":
        raw_id = str(value.get("prospect_id") or value.get("id") or "").strip()
        if not raw_id:
            basis = "|".join(
                str(value.get(key, "")).strip().lower()
                for key in ("name", "organization", "channel", "context")
            )
            raw_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
        return cls(
            prospect_id=raw_id,
            name=str(value.get("name", "")).strip(),
            organization=str(value.get("organization", "")).strip(),
            pain=str(value.get("pain", "")).strip(),
            budget_signal=str(value.get("budget_signal", "")).strip(),
            channel=str(value.get("channel", "")).strip(),
            context=str(value.get("context", "")).strip(),
        )

    def dedupe_key(self) -> str:
        basis = "|".join(
            [
                self.organization.casefold(),
                self.name.casefold(),
                self.channel.casefold(),
            ]
        )
        if not basis.strip("|"):
            basis = self.prospect_id.casefold()
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@dataclass
class StageResult:
    prospect_id: str
    stage: str
    status: str
    output: str = ""
    error: str = ""
    duration_s: float = 0.0
    approval_required: bool = False
    review_passed: Optional[bool] = None


@dataclass
class SwarmMetrics:
    rule: str = FOREVER_RULE
    requested_workers: int = 0
    active_workers: int = 0
    provider: str = "unknown"
    prospects_received: int = 0
    prospects_unique: int = 0
    prospects_deduped: int = 0
    pipelines_completed: int = 0
    stages_succeeded: int = 0
    stages_failed: int = 0
    awaiting_approval: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def duration_s(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.finished_at or time.time()
        return round(end - self.started_at, 3)


@dataclass
class SwarmConfig:
    requested_workers: int = field(
        default_factory=lambda: int(os.environ.get("GPT_DOUG_SWARM_WORKERS", "32"))
    )
    hard_max_workers: int = field(
        default_factory=lambda: int(os.environ.get("GPT_DOUG_SWARM_HARD_MAX", "64"))
    )
    local_provider_cap: int = field(
        default_factory=lambda: int(os.environ.get("GPT_DOUG_SWARM_LOCAL_CAP", "2"))
    )
    persist: bool = True


AgentRunner = Callable[[str, str, Prospect, str], dict]


def _provider_name() -> str:
    try:
        from agents import llm_backend

        state = llm_backend.health()
        return str(state.get("provider") or state.get("backend") or "unknown").lower()
    except Exception:
        return "unknown"


def _resolve_worker_count(config: SwarmConfig, provider: str) -> int:
    requested = max(1, int(config.requested_workers))
    hard_max = max(1, int(config.hard_max_workers))
    active = min(requested, hard_max)
    if provider == "ollama":
        active = min(active, max(1, int(config.local_provider_cap)))
    return active


def _default_runner(stage: str, prompt: str, prospect: Prospect, prior: str) -> dict:
    from agents import agent_chain

    task = (
        f"{ROLE_PROMPTS[stage]}\n\n"
        f"Prospect JSON:\n{json.dumps(asdict(prospect), indent=2)}\n\n"
        f"Prior pipeline context:\n{prior or '(none)'}\n\n"
        "Global rules: do not contact anyone, send messages, make purchases, "
        "move money, or perform irreversible external actions. Produce analysis "
        "or drafts only. Keep the output concise and evidence-linked."
    )
    trace = agent_chain.run(task)
    review = trace.get("review") or {}
    return {
        "output": trace.get("transcript", ""),
        "review_passed": review.get("passed"),
        "review": review,
        "run_id": trace.get("run_id"),
    }


class RevenueSwarm:
    def __init__(
        self,
        config: Optional[SwarmConfig] = None,
        runner: Optional[AgentRunner] = None,
    ):
        self.config = config or SwarmConfig()
        self.runner = runner or _default_runner
        self.provider = _provider_name()
        self.worker_count = _resolve_worker_count(self.config, self.provider)
        self.metrics = SwarmMetrics(
            requested_workers=self.config.requested_workers,
            active_workers=self.worker_count,
            provider=self.provider,
        )
        self._write_lock = threading.Lock()

    def _persist_record(self, record: dict) -> None:
        if not self.config.persist:
            return
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with RUN_LOG.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _persist_metrics(self) -> None:
        if not self.config.persist:
            return
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        payload = asdict(self.metrics)
        payload["duration_s"] = self.metrics.duration_s
        with self._write_lock:
            METRICS_FILE.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    def _run_stage(self, prospect: Prospect, stage: str, prior: str) -> StageResult:
        started = time.time()
        approval_required = stage == "outreach_draft"
        try:
            response = self.runner(stage, ROLE_PROMPTS[stage], prospect, prior) or {}
            output = str(response.get("output", "")).strip()
            review_passed = response.get("review_passed")
            result = StageResult(
                prospect_id=prospect.prospect_id,
                stage=stage,
                status="ok",
                output=output,
                duration_s=round(time.time() - started, 3),
                approval_required=approval_required,
                review_passed=review_passed,
            )
        except Exception as exc:
            result = StageResult(
                prospect_id=prospect.prospect_id,
                stage=stage,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                duration_s=round(time.time() - started, 3),
                approval_required=approval_required,
                review_passed=False,
            )
        self._persist_record(
            {
                "type": "stage_result",
                "ts": time.time(),
                "prospect": asdict(prospect),
                "result": asdict(result),
            }
        )
        return result

    def _run_pipeline(self, prospect: Prospect) -> dict:
        stage_results = []
        prior_parts = []
        for stage in STAGES:
            prior = "\n\n".join(prior_parts)[-12000:]
            result = self._run_stage(prospect, stage, prior)
            stage_results.append(result)
            if result.status != "ok":
                break
            prior_parts.append(f"[{stage}]\n{result.output}")
        completed = bool(stage_results) and stage_results[-1].stage == "qa"
        return {
            "prospect": asdict(prospect),
            "completed": completed,
            "results": [asdict(item) for item in stage_results],
            "approval_required": any(item.approval_required for item in stage_results),
        }

    def run(self, prospects: Iterable[Prospect]) -> dict:
        self.metrics.started_at = time.time()
        incoming = list(prospects)
        self.metrics.prospects_received = len(incoming)

        unique = []
        seen = set()
        for prospect in incoming:
            key = prospect.dedupe_key()
            if key in seen:
                self.metrics.prospects_deduped += 1
                continue
            seen.add(key)
            unique.append(prospect)
        self.metrics.prospects_unique = len(unique)

        pipelines = []
        with ThreadPoolExecutor(
            max_workers=self.worker_count,
            thread_name_prefix="gpt-doug-revenue-bee",
        ) as pool:
            futures = {pool.submit(self._run_pipeline, p): p for p in unique}
            for future in as_completed(futures):
                prospect = futures[future]
                try:
                    pipeline = future.result()
                except Exception as exc:
                    pipeline = {
                        "prospect": asdict(prospect),
                        "completed": False,
                        "results": [],
                        "approval_required": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                pipelines.append(pipeline)

        for pipeline in pipelines:
            if pipeline.get("completed"):
                self.metrics.pipelines_completed += 1
            for result in pipeline.get("results", []):
                if result.get("status") == "ok":
                    self.metrics.stages_succeeded += 1
                else:
                    self.metrics.stages_failed += 1
                if result.get("approval_required"):
                    self.metrics.awaiting_approval += 1

        self.metrics.finished_at = time.time()
        self._persist_metrics()
        return {
            "metrics": {
                **asdict(self.metrics),
                "duration_s": self.metrics.duration_s,
            },
            "pipelines": pipelines,
        }


def _load_prospects(path: Path) -> list[Prospect]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        values = json.loads(text)
    else:
        values = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [Prospect.from_mapping(item) for item in values]


def _demo_prospects() -> list[Prospect]:
    return [
        Prospect(
            prospect_id="demo-1",
            name="Example Operations Lead",
            organization="Example Manufacturing Co",
            pain="Manual intake and reporting create delays.",
            budget_signal="Evaluating automation vendors this quarter.",
            channel="demo",
            context="Synthetic demo record only.",
        ),
        Prospect(
            prospect_id="demo-2",
            name="Example Agency Owner",
            organization="Example Creative Studio",
            pain="Client onboarding and follow-up are repetitive.",
            budget_signal="Already pays for multiple SaaS tools.",
            channel="demo",
            context="Synthetic demo record only.",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded Sonoxo revenue swarm.")
    parser.add_argument("--input", type=Path, help="JSON array or JSONL prospect input.")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic demo prospects.")
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("GPT_DOUG_SWARM_WORKERS", "32")),
        help="Requested concurrent prospect pipelines.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write local JSONL audit/metrics files.",
    )
    args = parser.parse_args()

    if not args.demo and not args.input:
        parser.error("provide --input PATH or --demo")

    prospects = _demo_prospects() if args.demo else _load_prospects(args.input)
    swarm = RevenueSwarm(
        config=SwarmConfig(
            requested_workers=args.workers,
            persist=not args.no_persist,
        )
    )
    result = swarm.run(prospects)
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))
    return 0 if result["metrics"]["stages_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
