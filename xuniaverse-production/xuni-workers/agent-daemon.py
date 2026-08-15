#!/usr/bin/env python3
"""
Xuni Agent daemon (Doug Mode task runner).

Watches xuni-workers/tasks/*.json for task files, dispatches each to the
Doug agent via headless `claude -p --agent doug`, and writes the result to
xuni-workers/results/. Processed task files move to xuni-workers/processed/.

Task file format:
  {"id": "<string>", "prompt": "<string>"}
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zyra_guard

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "xuni-workers" / "tasks"
PROCESSED_DIR = ROOT / "xuni-workers" / "processed"
RESULTS_DIR = ROOT / "xuni-workers" / "results"
CONTEXT_LOG = ROOT / "xuni-workers" / "live" / "context.jsonl"
CONTEXT_WINDOW = 5
POLL_SECONDS = 0.5


def _recent_context() -> str:
    """Read the last CONTEXT_WINDOW completed tasks so Doug has real
    continuity across runs instead of treating every task as isolated."""
    if not CONTEXT_LOG.exists():
        return ""
    lines = CONTEXT_LOG.read_text().strip().splitlines()[-CONTEXT_WINDOW:]
    entries = []
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        summary = (rec.get("stdout") or rec.get("error") or "").strip()[:200]
        entries.append(f"- task {rec['id']!r} asked: {rec['prompt'][:200]!r} -> {summary!r}")
    if not entries:
        return ""
    return "Recent task history (most recent last):\n" + "\n".join(entries) + "\n\n"


def _append_context(task_id: str, prompt: str, result: dict):
    CONTEXT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {"id": task_id, "prompt": prompt, "stdout": result.get("stdout"), "error": result.get("error")}
    with CONTEXT_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")

# launchd runs this daemon with a minimal PATH that doesn't include the
# interactive shell's PATH, so a bare "claude" lookup fails even though it
# works fine from a terminal. Resolve a real path once at startup, checking
# common install locations if PATH itself comes up empty.
def _resolve_claude_bin() -> str:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ):
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("claude binary not found in PATH or common install locations")


CLAUDE_BIN = _resolve_claude_bin()

for d in (TASKS_DIR, PROCESSED_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def run_task(task_path: Path):
    try:
        task = json.loads(task_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[skip] {task_path.name}: invalid task file ({e})", flush=True)
        task_path.rename(PROCESSED_DIR / task_path.name)
        return

    task_id = task.get("id", task_path.stem)
    prompt = task.get("prompt")
    if not prompt:
        print(f"[skip] {task_path.name}: missing 'prompt'", flush=True)
        task_path.rename(PROCESSED_DIR / task_path.name)
        return

    allowed, reason = zyra_guard.review(task)
    if not allowed:
        print(f"[blocked] {task_id}: zyra rejected task ({reason})", flush=True)
        (RESULTS_DIR / f"{task_id}.json").write_text(json.dumps(
            {"id": task_id, "prompt": prompt, "blocked_by": "zyra", "reason": reason}, indent=2
        ))
        task_path.rename(PROCESSED_DIR / task_path.name)
        return

    print(f"[run] {task_id}: zyra cleared, dispatching to doug agent", flush=True)
    started = time.time()
    context_prefix = _recent_context()
    full_prompt = context_prefix + prompt
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "-p", "--agent", "doug", full_prompt],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        result = {
            "id": task_id,
            "prompt": prompt,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_seconds": round(time.time() - started, 2),
        }
        print(f"[done] {task_id}: exit={proc.returncode} in {result['duration_seconds']}s", flush=True)
    except Exception as e:
        result = {
            "id": task_id,
            "prompt": prompt,
            "error": f"{type(e).__name__}: {e}",
            "duration_seconds": round(time.time() - started, 2),
        }
        print(f"[error] {task_id}: dispatch failed ({e})", flush=True)
    finally:
        # Always retire the task file, even on failure — a task must never
        # be left to retry forever and crash-loop the daemon.
        (RESULTS_DIR / f"{task_id}.json").write_text(json.dumps(result, indent=2))
        _append_context(task_id, prompt, result)
        task_path.rename(PROCESSED_DIR / task_path.name)


def main():
    print("xuni agent daemon started, watching", TASKS_DIR, flush=True)
    while True:
        for task_path in sorted(TASKS_DIR.glob("*.json")):
            try:
                run_task(task_path)
            except Exception as e:
                # Never let one bad task file kill the daemon loop.
                print(f"[error] unhandled failure on {task_path.name}: {e}", flush=True)
                if task_path.exists():
                    task_path.rename(PROCESSED_DIR / task_path.name)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
