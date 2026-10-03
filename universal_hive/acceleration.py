from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


_LOCAL_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


class AdaptiveAutomationAccelerator:
    """Evidence-bound automation learning loop for GPT-Doug/GPT-Chaos.

    This module implements a generalized architecture inspired by observed RPA
    pipeline patterns: normalize pipeline events, build reusable composites,
    induce bounded rules from history, generate templates, and produce
    non-executable setup objects.

    The runtime does not execute generated code or widen permissions. Learned
    guidance is advisory until a deterministic executor and existing approval
    controls accept it.
    """

    SOURCE = {
        "type": "patent_architecture_reference",
        "document": "US Patent 12,737,161",
        "title": "Robotic process automation acceleration and control",
        "date": "2026-09-15",
        "assignee": "The Huntington National Bank",
        "use": "generalized architecture inspiration; independent implementation",
    }

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.state_dir / "automation-events.jsonl"
        self.composites_path = self.state_dir / "automation-composites.json"
        self.rules_path = self.state_dir / "learned-rules.json"
        self.templates_path = self.state_dir / "templates.json"
        self.lock_path = self.state_dir / ".lock"

        for path, default in (
            (self.composites_path, {"schema": "adaptive-automation/composites-v1", "items": {}}),
            (self.rules_path, {"schema": "adaptive-automation/rules-v1", "automation_types": {}}),
            (self.templates_path, {"schema": "adaptive-automation/templates-v1", "automation_types": {}}),
        ):
            if not path.exists():
                _atomic_write_json(path, default)

    class _Lock:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.handle = None

        def __enter__(self):
            _LOCAL_LOCK.acquire()
            self.handle = self.path.open("a+", encoding="utf-8")
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                if self.handle is not None:
                    self.handle.close()
            finally:
                _LOCAL_LOCK.release()

    def _lock(self):
        return self._Lock(self.lock_path)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    @staticmethod
    def _normalize_requirements(requirements: Optional[Iterable[str]]) -> list[str]:
        seen = set()
        result = []
        for requirement in requirements or ():
            value = " ".join(str(requirement).split()).strip()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def record_event(
        self,
        *,
        automation_type: str,
        stage: str,
        status: str,
        attributes: Optional[Mapping[str, Any]] = None,
        requirements: Optional[Iterable[str]] = None,
        metrics: Optional[Mapping[str, Any]] = None,
        source: str = "runtime",
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        kind = " ".join(str(automation_type).split()).strip().lower()
        stage_name = " ".join(str(stage).split()).strip().lower()
        state = " ".join(str(status).split()).strip().upper()
        if not kind or not stage_name or not state:
            raise ValueError("automation_type, stage, and status are required")

        identity = {
            "automation_type": kind,
            "stage": stage_name,
            "status": state,
            "attributes": dict(attributes or {}),
            "requirements": self._normalize_requirements(requirements),
            "metrics": dict(metrics or {}),
            "source": str(source),
            "run_id": run_id,
        }
        event = {
            "schema": "adaptive-automation/event-v1",
            "event_id": "ae-" + hashlib.sha256(_canonical(identity)).hexdigest()[:24],
            "recorded_at": _utc_now(),
            **identity,
        }

        with self._lock():
            existing_ids = {row.get("event_id") for row in self._events()}
            if event["event_id"] not in existing_ids:
                with self.events_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            self._rebuild_models_locked()
        return event

    def observe_hivemind_run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        plan = dict(payload.get("plan") or {})
        metadata = dict(plan.get("metadata") or {})
        run_id = str(metadata.get("mission_id") or "")
        results = list(payload.get("results") or [])
        recorded = []
        for result in results:
            row = dict(result)
            stage = str(row.get("stage") or "unknown")
            status = str(row.get("status") or "UNKNOWN")
            integration = row.get("integration")
            attributes = {
                "integration": integration,
                "item_id": row.get("item_id"),
                "controller": metadata.get("controller"),
                "simulation_layer": metadata.get("simulation_layer"),
            }
            requirements = [
                "preserve_provenance",
                "validate_before_external_mutation",
                "keep_rollback_path",
            ]
            recorded.append(
                self.record_event(
                    automation_type="hivemind",
                    stage=stage,
                    status=status,
                    attributes=attributes,
                    requirements=requirements,
                    source="hivemind.execute",
                    run_id=run_id or None,
                )
            )
        return {
            "recorded_events": len(recorded),
            "run_id": run_id or None,
            "template": self.template("hivemind"),
        }

    def _rebuild_models_locked(self) -> None:
        events = self._events()
        composites: dict[str, Any] = {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for event in events:
            composite_payload = {
                "automation_type": event["automation_type"],
                "stage": event["stage"],
                "status": event["status"],
                "attributes": event.get("attributes") or {},
                "requirements": event.get("requirements") or [],
                "metrics": event.get("metrics") or {},
            }
            composite_id = "ac-" + hashlib.sha256(_canonical(composite_payload)).hexdigest()[:24]
            current = composites.setdefault(
                composite_id,
                {
                    "composite_id": composite_id,
                    "automation_type": event["automation_type"],
                    "stage": event["stage"],
                    "status": event["status"],
                    "attributes": event.get("attributes") or {},
                    "requirements": event.get("requirements") or [],
                    "metrics": event.get("metrics") or {},
                    "observations": 0,
                    "source_event_ids": [],
                },
            )
            current["observations"] += 1
            current["source_event_ids"].append(event["event_id"])
            grouped[event["automation_type"]].append(event)

        rules: dict[str, Any] = {}
        templates: dict[str, Any] = {}

        for automation_type, rows in grouped.items():
            stage_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
            requirement_counts: Counter[str] = Counter()
            for row in rows:
                stage_rows[row["stage"]].append(row)
                requirement_counts.update(row.get("requirements") or [])

            stage_rules: dict[str, Any] = {}
            failure_watchlist = []
            for stage, samples in stage_rows.items():
                total = len(samples)
                successful = [
                    sample for sample in samples
                    if sample["status"] in {"PASSED", "READY", "SUCCEEDED", "SUCCESS"}
                ]
                success_rate = len(successful) / total if total else 0.0
                integrations = Counter(
                    str((sample.get("attributes") or {}).get("integration"))
                    for sample in successful
                    if (sample.get("attributes") or {}).get("integration")
                )
                preferred = integrations.most_common(1)[0][0] if integrations else None
                failure_rate = 1.0 - success_rate
                if total >= 4 and failure_rate >= 0.25:
                    failure_watchlist.append(stage)
                stage_rules[stage] = {
                    "observations": total,
                    "success_rate": round(success_rate, 4),
                    "preferred_integration": preferred,
                    "confidence": round(min(1.0, total / 10.0), 4),
                }

            requirements = [
                requirement
                for requirement, count in requirement_counts.most_common()
                if count >= max(1, len(rows) // 2)
            ]
            rules[automation_type] = {
                "observations": len(rows),
                "stage_rules": stage_rules,
                "requirements": requirements,
                "failure_watchlist": sorted(failure_watchlist),
                "generated_at": _utc_now(),
                "policy": {
                    "learned_guidance_is_advisory": True,
                    "deterministic_validation_required": True,
                    "external_mutation_requires_existing_authorization": True,
                    "generated_code_execution": False,
                },
            }
            templates[automation_type] = {
                "template_id": "tpl-" + hashlib.sha256(
                    _canonical({"automation_type": automation_type, "rules": rules[automation_type]})
                ).hexdigest()[:24],
                "automation_type": automation_type,
                "prepopulated": {
                    "preferred_integrations": {
                        stage: data["preferred_integration"]
                        for stage, data in stage_rules.items()
                        if data["preferred_integration"] is not None and data["confidence"] >= 0.2
                    },
                    "requirements": requirements,
                    "failure_watchlist": sorted(failure_watchlist),
                },
                "validation": {
                    "require_provenance": True,
                    "require_explicit_external_authorization": True,
                    "require_rollback_for_mutation": True,
                },
                "source": self.SOURCE,
                "generated_at": _utc_now(),
            }

        _atomic_write_json(
            self.composites_path,
            {
                "schema": "adaptive-automation/composites-v1",
                "source": self.SOURCE,
                "items": composites,
            },
        )
        _atomic_write_json(
            self.rules_path,
            {
                "schema": "adaptive-automation/rules-v1",
                "source": self.SOURCE,
                "automation_types": rules,
            },
        )
        _atomic_write_json(
            self.templates_path,
            {
                "schema": "adaptive-automation/templates-v1",
                "source": self.SOURCE,
                "automation_types": templates,
            },
        )

    def template(self, automation_type: str) -> dict[str, Any]:
        kind = " ".join(str(automation_type).split()).strip().lower()
        payload = self._read_json(self.templates_path)
        return dict((payload.get("automation_types") or {}).get(kind) or {})

    def generate_setup_object(
        self,
        automation_type: str,
        *,
        explicit_input: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        kind = " ".join(str(automation_type).split()).strip().lower()
        template = self.template(kind)
        if not template:
            raise KeyError(f"no learned template for automation type: {kind}")

        setup_payload = {
            "automation_type": kind,
            "template_id": template["template_id"],
            "explicit_input": dict(explicit_input or {}),
            "learned_defaults": dict(template.get("prepopulated") or {}),
            "validation": dict(template.get("validation") or {}),
            "source": self.SOURCE,
            "generated_at": _utc_now(),
            "execution": "NON_EXECUTABLE_SETUP_OBJECT",
        }
        setup_payload["setup_object_id"] = "aso-" + hashlib.sha256(
            _canonical(setup_payload)
        ).hexdigest()[:24]
        return setup_payload

    def status(self) -> dict[str, Any]:
        events = self._events()
        composites = self._read_json(self.composites_path)
        rules = self._read_json(self.rules_path)
        templates = self._read_json(self.templates_path)
        return {
            "status": "ACTIVE",
            "event_count": len(events),
            "composite_count": len(composites.get("items") or {}),
            "automation_types": sorted((rules.get("automation_types") or {}).keys()),
            "template_count": len(templates.get("automation_types") or {}),
            "state_dir": str(self.state_dir),
            "source": self.SOURCE,
            "boundaries": {
                "generated_code_execution": False,
                "permission_widening": False,
                "learned_guidance_is_advisory": True,
            },
        }
