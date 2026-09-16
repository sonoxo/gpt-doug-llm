"""Unified ontology bridge for GPT Doug.

Stable interface over:
- agents/ontology.py: task-graph validation.
- workers/ontology_workers.py: Task/Result/KnowledgeEntry objects, links and actions.
- workers/arcade_ontology.py: ArcadeRun/BountyClaim objects and XUNIA bounty actions.
- reef_bridge.py: optional continual-learning lifecycle registration.
- flipper_ontology.py: governed Flipper Zero edge-device and digital-twin ontology.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_module(name: str, path: Path):
    full_name = f"_doung_ontology_{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


_task_graph = _load_module("task_graph", _ROOT / "agents" / "ontology.py")
_workers_ont = _load_module("workers_ont", _ROOT / "workers" / "ontology_workers.py")
_arcade_ont = _load_module("arcade_ont", _ROOT / "workers" / "arcade_ontology.py")
_reef_bridge = _load_module("reef_bridge", _ROOT / "reef_bridge.py")
_flipper_ont = _load_module("flipper_ont", _ROOT / "flipper_ontology.py")


class Ontology:
    """Unified ontology access for planning, workers, arcade, Reef, and Flipper."""

    @staticmethod
    def validate_plan(data: dict) -> dict:
        return _task_graph.validate_task_graph(data)

    @staticmethod
    def extract_plan_json(text: str) -> str:
        return _task_graph.extract_json_object(text)

    @staticmethod
    def schema_description() -> str:
        return _task_graph.TASK_GRAPH_SCHEMA_DESCRIPTION

    @staticmethod
    def valid_roles() -> set:
        return set(_task_graph.VALID_AGENT_ROLES)

    @staticmethod
    def tasks() -> list:
        return _workers_ont.list_tasks()

    @staticmethod
    def results() -> list:
        return _workers_ont.list_results()

    @staticmethod
    def knowledge() -> list:
        return _workers_ont.list_knowledge()

    @staticmethod
    def task_result(task_id: str) -> dict:
        return _workers_ont.link_task_to_result(task_id)

    @staticmethod
    def task_knowledge(task_id: str, prompt: str, top_n: int = 3) -> list:
        return _workers_ont.link_task_to_knowledge(task_id, prompt, top_n)

    @staticmethod
    def submit_task(task_id: str, prompt: str) -> dict:
        """Zyra-gated SubmitTask action."""
        return _workers_ont.submit_task_action(task_id, prompt)

    @staticmethod
    def arcade_bounties() -> dict:
        """Return deterministic game -> ontology-function bounty catalog."""
        return _arcade_ont.bounty_catalog()

    @staticmethod
    def record_arcade_run(receipt: dict) -> dict:
        """Validate a browser receipt, execute its bounded ontology function and award XBC."""
        return _arcade_ont.record_arcade_run_action(receipt)

    @staticmethod
    def arcade_runs() -> list:
        return _arcade_ont.list_arcade_runs()

    @staticmethod
    def bounty_claims() -> list:
        return _arcade_ont.list_bounty_claims()

    @staticmethod
    def bounty_balance() -> dict:
        return _arcade_ont.bounty_balance()

    @staticmethod
    def reef_schema() -> dict:
        return _reef_bridge.ReefBridge.ontology_registration()

    @staticmethod
    def reef(config=None):
        return _reef_bridge.ReefBridge(config)

    @staticmethod
    def flipper():
        """Return the governed process-local Flipper Zero ontology runtime."""
        return _flipper_ont.runtime()

    @staticmethod
    def flipper_status() -> dict:
        """Return Flipper ontology object counts and policy state."""
        return _flipper_ont.runtime().summary()

    @staticmethod
    def status() -> dict:
        core = _workers_ont.summary()
        core["arcade"] = _arcade_ont.bounty_balance()
        core["flipper"] = _flipper_ont.runtime().summary()
        return core

    @staticmethod
    def snapshot() -> dict:
        return _workers_ont.write_snapshot()

    @staticmethod
    def display() -> str:
        s = _workers_ont.summary()
        b = _arcade_ont.bounty_balance()
        f = _flipper_ont.runtime().summary()
        lines = [
            "ONTOLOGY // UNIFIED SEMANTIC MODEL",
            "  Object types: Task, Result, KnowledgeEntry, ArcadeRun, BountyClaim, FlipperDevice, Asset, Authorization, TestSession, Observation, DigitalTwin, AuditEvent",
            f"  Tasks: {s['object_counts']['Task']}",
            f"  Results: {s['object_counts']['Result']}",
            f"  Knowledge entries: {s['object_counts']['KnowledgeEntry']}",
            f"  Active links: {s['link_count']}",
            f"  Arcade bounty claims: {b['claim_count']}",
            f"  Arcade XBC awarded: {b['awarded']}",
            f"  Flipper devices: {f['object_counts']['FlipperDevice']}",
            f"  Flipper test sessions: {f['object_counts']['TestSession']}",
            f"  Flipper digital twins: {f['object_counts']['DigitalTwin']}",
            f"  Task-graph schema: {len(_task_graph.VALID_AGENT_ROLES)} agent roles",
            "  Action types: SubmitTask (Zyra-gated), RecordArcadeRun, Flipper governed actions",
            "  Flipper policy: deny-by-default; physical actuation staged only",
            "  Continual learning: Reef registered (Serve → Observe → Grow → Commit)",
        ]
        return "\n".join(lines)
