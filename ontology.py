"""Unified ontology bridge for GPT Doug.

Connects two ontology systems that previously lived in separate modules:

  1. agents/ontology.py — Task-graph schema for multi-agent planning
     (Task → Steps → Artifacts → Constraints → Agent roles)
     Used by agent_chain.py to structure the planner's output.

  2. workers/ontology_workers.py — Foundry-inspired object/link/action model
     (Object Types: Task, Result, KnowledgeEntry)
     (Link Types: produced, referenced)
     (Action Types: SubmitTask — routed through Zyra)
     Used by agent-daemon.py for task dispatch and knowledge retrieval.

This bridge lets the terminal client (gpt-doug), the agent chain, and the
worker daemon all share one coherent semantic model without either side
losing its existing interface.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_module(name: str, path: Path):
    """Load a module from a specific file path, avoiding circular imports."""
    full_name = f"_doung_ontology_{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load agents/ontology.py (task-graph schema)
_task_graph = _load_module("task_graph", _ROOT / "agents" / "ontology.py")

# Load workers/ontology_workers.py (Foundry-inspired object/link/action)
_workers_ont = _load_module("workers_ont", _ROOT / "workers" / "ontology_workers.py")


class Ontology:
    """Unified ontology access for GPT Doug.

    Combines task-graph validation (for multi-agent planning) with the
    Foundry-inspired object/link/action model (for task management and
    knowledge retrieval). All action types go through Zyra.
    """

    # --- Task-graph schema (agents/ontology.py) ---

    @staticmethod
    def validate_plan(data: dict) -> dict:
        """Validate a parsed task-graph plan from the planner agent."""
        return _task_graph.validate_task_graph(data)

    @staticmethod
    def extract_plan_json(text: str) -> str:
        """Extract the first JSON object from model output."""
        return _task_graph.extract_json_object(text)

    @staticmethod
    def schema_description() -> str:
        """Return the schema prompt for the planner agent."""
        return _task_graph.TASK_GRAPH_SCHEMA_DESCRIPTION

    @staticmethod
    def valid_roles() -> set:
        return set(_task_graph.VALID_AGENT_ROLES)

    # --- Object types (workers/ontology_workers.py) ---

    @staticmethod
    def tasks() -> list:
        """List all Task objects (queued + processed)."""
        return _workers_ont.list_tasks()

    @staticmethod
    def results() -> list:
        """List all Result objects."""
        return _workers_ont.list_results()

    @staticmethod
    def knowledge() -> list:
        """List all KnowledgeEntry objects from the knowledge base."""
        return _workers_ont.list_knowledge()

    # --- Link types ---

    @staticmethod
    def task_result(task_id: str) -> dict:
        """Link: Task --produced--> Result."""
        return _workers_ont.link_task_to_result(task_id)

    @staticmethod
    def task_knowledge(task_id: str, prompt: str, top_n: int = 3) -> list:
        """Link: Task --referenced--> KnowledgeEntry (keyword-scored)."""
        return _workers_ont.link_task_to_knowledge(task_id, prompt, top_n)

    # --- Action types (Zyra-gated) ---

    @staticmethod
    def submit_task(task_id: str, prompt: str) -> dict:
        """Action: SubmitTask — writes a task file for the daemon to pick up.
        Routed through Zyra guard; rejected if the prompt is unsafe."""
        return _workers_ont.submit_task_action(task_id, prompt)

    # --- Summary ---

    @staticmethod
    def status() -> dict:
        """Return a summary of all objects and links."""
        return _workers_ont.summary()

    @staticmethod
    def snapshot() -> dict:
        """Persist a timestamped snapshot of the ontology state."""
        return _workers_ont.write_snapshot()

    # --- Display ---

    @staticmethod
    def display() -> str:
        """Human-readable ontology status for the terminal client."""
        s = _workers_ont.summary()
        lines = [
            "ONTOLOGY // UNIFIED SEMANTIC MODEL",
            f"  Object types: Task, Result, KnowledgeEntry",
            f"  Tasks: {s['object_counts']['Task']}",
            f"  Results: {s['object_counts']['Result']}",
            f"  Knowledge entries: {s['object_counts']['KnowledgeEntry']}",
            f"  Active links: {s['link_count']}",
            f"  Task-graph schema: {len(_task_graph.VALID_AGENT_ROLES)} agent roles",
            f"  Action types: SubmitTask (Zyra-gated)",
        ]
        return "\n".join(lines)
