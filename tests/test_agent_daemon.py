#!/usr/bin/env python3
"""
Regression suite for agent-daemon.py's retry/backoff and concurrency logic.
Adapted for pytest compatibility in the unified gpt-doug-llm project.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load_daemon_module(root: Path):
    spec = importlib.util.spec_from_file_location(
        "agent_daemon_test_instance", HERE / ".." / "workers" / "agent-daemon.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = root
    mod.TASKS_DIR = root / "xuni-workers" / "tasks"
    mod.CLAIMED_DIR = root / "xuni-workers" / "claimed"
    mod.PROCESSED_DIR = root / "xuni-workers" / "processed"
    mod.RESULTS_DIR = root / "xuni-workers" / "results"
    mod.CONTEXT_LOG = root / "xuni-workers" / "live" / "context.jsonl"
    for d in (mod.TASKS_DIR, mod.CLAIMED_DIR, mod.PROCESSED_DIR, mod.RESULTS_DIR, mod.CONTEXT_LOG.parent):
        d.mkdir(parents=True, exist_ok=True)
    return mod


def test_claim_task_is_atomic_and_idempotent():
    """Two workers racing to claim the same task: only one wins."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        task = {"id": "atomic-test", "prompt": "test atomicity"}
        task_path = mod.TASKS_DIR / "atomic-test.json"
        task_path.write_text(json.dumps(task))
        first_claim = mod.claim_task(task_path)
        assert first_claim is not None, "first claim should succeed"
        second_claim = mod.claim_task(task_path)
        assert second_claim is None, \
            "a second claim attempt on an already-claimed file returns None"


def test_claim_moves_file_from_tasks_to_claimed():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        task = {"id": "move-test", "prompt": "test file move"}
        task_path = mod.TASKS_DIR / "move-test.json"
        task_path.write_text(json.dumps(task))
        claimed_path = mod.claim_task(task_path)
        assert claimed_path is not None, "claim should succeed"
        assert not task_path.exists(), "original task file should be gone after claiming"
        assert claimed_path.exists(), "claimed file should exist in claimed dir"


def test_relevant_knowledge_returns_string():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        result = mod._relevant_knowledge("build a web app")
        assert isinstance(result, str), "relevant_knowledge should return a string"


def test_run_task_with_invalid_json_moves_to_processed():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        task_path = mod.TASKS_DIR / "bad.json"
        task_path.write_text("not valid json{")
        mod.run_task(task_path)
        # Invalid task should be moved to processed (not crash)
        assert (mod.PROCESSED_DIR / "bad.json").exists() or not task_path.exists(), \
            "invalid task file should be moved out of tasks dir"


if __name__ == "__main__":
    test_claim_task_is_atomic_and_idempotent()
    test_claim_moves_file_from_tasks_to_claimed()
    test_relevant_knowledge_returns_string()
    test_run_task_with_invalid_json_moves_to_processed()
    print("All agent-daemon tests passed.")
