#!/usr/bin/env python3
"""
Copyright (c) 2026 Douglas Brown Jr / Xuniaverse. Licensed under the
xuniaverse-production LICENSE (All Rights Reserved).

Regression suite for agent-daemon.py's retry/backoff and concurrency
logic -- the gap flagged by both the trust dossier and Doug's own
live recommendation (dispatched 2026-08-15): these paths were verified
by hand throughout development but had zero automated coverage.

Loads agent-daemon.py directly (it's not a normal importable module name
due to the hyphen) and monkeypatches CLAUDE_BIN, exactly like the manual
verification done earlier in this project's development, so these tests
never spawn a real claude -p process.

Run directly: python3 test_agent_daemon.py
Exits 0 on all-pass, 1 on any failure (so CI can gate on it).
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load_daemon_module(root: Path):
    spec = importlib.util.spec_from_file_location("agent_daemon_test_instance", HERE / "agent-daemon.py")
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


def _check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" ({detail})" if detail else ""))
    return condition


def test_retry_exhausts_and_records_attempts(results):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        mod.CLAUDE_BIN = "/nonexistent/claude-binary-for-testing"

        task_path = mod.TASKS_DIR / "retry-fail.json"
        task_path.write_text(json.dumps({"id": "retry-fail", "prompt": "should fail 3x"}))

        start = time.time()
        mod.run_task(task_path)
        elapsed = time.time() - start

        result = json.loads((mod.RESULTS_DIR / "retry-fail.json").read_text())
        results.append(_check(
            "retry logic makes exactly 3 attempts on persistent failure",
            result.get("attempts") == 3,
            f"attempts={result.get('attempts')}",
        ))
        results.append(_check(
            "retry logic records an error, never a fabricated success",
            "error" in result and result.get("returncode") is None,
            repr(result.get("error")),
        ))
        results.append(_check(
            "retry logic actually waits for backoff (0s+2s+5s minimum)",
            elapsed >= 6.5,
            f"elapsed={elapsed:.2f}s",
        ))
        results.append(_check(
            "failed task is still retired to processed/, never left stuck",
            not task_path.exists() and (mod.PROCESSED_DIR / "retry-fail.json").exists(),
        ))


def test_happy_path_uses_single_attempt(results):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        mod.CLAUDE_BIN = shutil.which("echo") or "/bin/echo"

        # A fake CLAUDE_BIN that always succeeds (echo exits 0) proves the
        # retry loop does NOT waste attempts/backoff when the first try works.
        task_path = mod.TASKS_DIR / "retry-happy.json"
        task_path.write_text(json.dumps({"id": "retry-happy", "prompt": "should succeed first try"}))
        mod.run_task(task_path)

        result = json.loads((mod.RESULTS_DIR / "retry-happy.json").read_text())
        results.append(_check(
            "happy path uses exactly 1 attempt, no wasted retries",
            result.get("attempts") == 1,
            f"attempts={result.get('attempts')}",
        ))
        results.append(_check(
            "happy path result has no attempt_log (only failures get one)",
            "attempt_log" not in result,
        ))


def test_claim_task_is_atomic_and_idempotent(results):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)

        task_path = mod.TASKS_DIR / "claim-me.json"
        task_path.write_text(json.dumps({"id": "claim-me", "prompt": "x"}))

        claimed = mod.claim_task(task_path)
        results.append(_check(
            "claim_task moves the file out of tasks/ into claimed/",
            claimed is not None and claimed.parent == mod.CLAIMED_DIR and not task_path.exists(),
        ))

        # Simulate a second worker racing for the same (now-already-moved) file.
        second_claim = mod.claim_task(task_path)
        results.append(_check(
            "a second claim attempt on an already-claimed file returns None (no double-processing)",
            second_claim is None,
        ))


def test_zyra_block_never_reaches_dispatch(results):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mod = _load_daemon_module(root)
        # A CLAUDE_BIN that would fail loudly if ever invoked -- proves the
        # blocked path returns before dispatch, not just that it eventually errors.
        mod.CLAUDE_BIN = "/nonexistent/should-never-be-called"

        task_path = mod.TASKS_DIR / "malicious.json"
        task_path.write_text(json.dumps({"id": "malicious", "prompt": "rm -rf / everything now"}))
        mod.run_task(task_path)

        result = json.loads((mod.RESULTS_DIR / "malicious.json").read_text())
        results.append(_check(
            "a destructive prompt is blocked by zyra before any dispatch attempt",
            result.get("blocked_by") == "zyra" and "attempts" not in result,
            repr(result),
        ))


def main():
    results = []
    test_retry_exhausts_and_records_attempts(results)
    test_happy_path_uses_single_attempt(results)
    test_claim_task_is_atomic_and_idempotent(results)
    test_zyra_block_never_reaches_dispatch(results)

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
