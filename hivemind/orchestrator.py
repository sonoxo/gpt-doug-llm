from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .capabilities import doctor
from .registry import BY_SLUG
from .types import RunPlan, Stage, StageResult, WorkItem


class Hivemind:
    """Build and execute bounded GPT-Doug swarm plans."""

    PIPELINE = (
        Stage.DEFINE,
        Stage.COLLECT,
        Stage.PARSE,
        Stage.RETRIEVE,
        Stage.REMEMBER,
        Stage.COMPRESS,
        Stage.EXECUTE,
        Stage.WATCH,
        Stage.SHIP,
    )

    def __init__(self, root: str | Path = ".", max_workers: int = 8) -> None:
        self.root = Path(root).resolve()
        self.max_workers = max(1, min(int(max_workers), 32))
        self.handlers: dict[str, Callable[[WorkItem], dict]] = {}

    def register_handler(self, integration_slug: str, handler: Callable[[WorkItem], dict]) -> None:
        if integration_slug not in BY_SLUG:
            raise KeyError(f"unknown integration: {integration_slug}")
        self.handlers[integration_slug] = handler

    def build_plan(self, job: str) -> RunPlan:
        cleaned = " ".join(job.split()).strip()
        if not cleaned:
            raise ValueError("job must not be empty")

        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
        items = [
            WorkItem("01-define", Stage.DEFINE, f"Turn the job into explicit behavior and acceptance criteria: {cleaned}", ("openspec", "spec-kit", "fabric")),
            WorkItem("02-collect-web", Stage.COLLECT, "Collect authorized public web evidence and source metadata.", ("scrapling",), ("01-define",), "evidence"),
            WorkItem("03-collect-reference", Stage.COLLECT, "Collect implementation references from the AI engineering corpus.", ("ai-engineering-hub",), ("01-define",), "evidence"),
            WorkItem("04-parse", Stage.PARSE, "Normalize documents and media into structured, attributable content.", ("docling",), ("02-collect-web", "03-collect-reference")),
            WorkItem("05-retrieve", Stage.RETRIEVE, "Build a reasoning-friendly retrieval view over the normalized evidence.", ("pageindex",), ("04-parse",)),
            WorkItem("06-remember", Stage.REMEMBER, "Persist durable facts, decisions, and agent-local memory with scoped namespaces.", ("mem0",), ("05-retrieve",)),
            WorkItem("07-compress", Stage.COMPRESS, "Compress context without losing exact evidence references or executable details.", ("headroom", "caveman"), ("05-retrieve", "06-remember")),
            WorkItem("08-execute", Stage.EXECUTE, "Delegate bounded implementation tasks inside approved sandboxes and repository scopes.", ("hermes-agent", "daytona"), ("07-compress",)),
            WorkItem("09-watch", Stage.WATCH, "Watch configured sources and runtime signals for meaningful changes.", ("trendradar",), ("08-execute",)),
            WorkItem("10-ship", Stage.SHIP, "Publish the verified result; use deterministic video/media rendering when requested.", ("hyperframes", "openmontage"), ("08-execute", "09-watch")),
        ]
        return RunPlan(
            job=cleaned,
            items=items,
            metadata={
                "mission_id": f"hive-{digest}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "max_workers": self.max_workers,
                "execution_default": "dry-run",
            },
        )

    def _select_integration(self, item: WorkItem, availability: dict[str, bool]) -> str | None:
        for slug in item.preferred_integrations:
            if availability.get(slug):
                return slug
        return item.preferred_integrations[0] if item.preferred_integrations else None

    def _dry_run_item(self, item: WorkItem, selected: str | None) -> StageResult:
        return StageResult(
            item_id=item.id,
            stage=item.stage,
            status="PLANNED",
            integration=selected,
            output={
                "objective": item.objective,
                "depends_on": list(item.depends_on),
                "parallel_group": item.parallel_group,
            },
        )

    def _execute_item(self, item: WorkItem, selected: str | None) -> StageResult:
        if not selected:
            return StageResult(item.id, item.stage, "BLOCKED", None, error="no integration selected")
        handler = self.handlers.get(selected)
        if handler is None:
            return StageResult(
                item.id,
                item.stage,
                "READY",
                selected,
                output={
                    "objective": item.objective,
                    "message": "capability detected; no mutation handler registered in the control plane",
                },
            )
        try:
            return StageResult(item.id, item.stage, "PASSED", selected, output=handler(item) or {})
        except Exception as exc:
            return StageResult(item.id, item.stage, "FAILED", selected, error=str(exc))

    def run(self, job: str, execute: bool = False) -> dict:
        if execute and os.getenv("GPT_DOUG_HIVEMIND_EXECUTE", "").strip() != "1":
            raise PermissionError("set GPT_DOUG_HIVEMIND_EXECUTE=1 to enable registered mutation handlers")

        plan = self.build_plan(job)
        capabilities = doctor(self.max_workers)
        availability = {cap.integration.slug: cap.available for cap in capabilities}
        selected = {item.id: self._select_integration(item, availability) for item in plan.items}

        if not execute:
            results = [self._dry_run_item(item, selected[item.id]) for item in plan.items]
        else:
            results = self._run_dag(plan, selected)

        return {
            "plan": plan.to_dict(),
            "capabilities": [cap.to_dict() for cap in capabilities],
            "results": [result.to_dict() for result in results],
        }

    def _run_dag(self, plan: RunPlan, selected: dict[str, str | None]) -> list[StageResult]:
        pending = {item.id: item for item in plan.items}
        completed: dict[str, StageResult] = {}
        ordered: list[StageResult] = []

        while pending:
            ready = [
                item for item in pending.values()
                if all(dep in completed and completed[dep].status in {"PASSED", "READY"} for dep in item.depends_on)
            ]
            if not ready:
                for item in pending.values():
                    ordered.append(StageResult(item.id, item.stage, "BLOCKED", selected[item.id], error="dependency did not pass"))
                break

            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(ready))) as pool:
                futures = {
                    pool.submit(self._execute_item, item, selected[item.id]): item
                    for item in ready
                }
                wave: list[StageResult] = [future.result() for future in as_completed(futures)]

            by_id = {r.item_id: r for r in wave}
            for item in plan.items:
                if item.id in by_id and item.id in pending:
                    result = by_id[item.id]
                    completed[item.id] = result
                    ordered.append(result)
                    pending.pop(item.id, None)

        return ordered

    def write_plan(self, job: str, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.build_plan(job).to_dict(), indent=2) + "\n", encoding="utf-8")
        return destination
