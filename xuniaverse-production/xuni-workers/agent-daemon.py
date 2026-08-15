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
KNOWLEDGE_DIR = ROOT / "xuni-workers" / "knowledge"
CONTEXT_WINDOW = 5
KNOWLEDGE_MATCHES = 3
POLL_SECONDS = 0.5


def _load_knowledge() -> list:
    """Load every *.jsonl file in xuni-workers/knowledge/. Each line is one
    attributed, summarized entry — never a verbatim transcript — with an
    id, topic, attribution, summary, and keyword list for retrieval."""
    entries = []
    if not KNOWLEDGE_DIR.exists():
        return entries
    for path in sorted(KNOWLEDGE_DIR.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _relevant_knowledge(prompt: str) -> str:
    """Keyword-match the prompt against the knowledge base and return the
    top matches as a labeled, attributed context block. Real retrieval —
    scored by keyword overlap, not fabricated relevance."""
    entries = _load_knowledge()
    if not entries:
        return ""
    lower = prompt.lower()
    scored = []
    for entry in entries:
        score = sum(1 for kw in entry.get("keywords", []) if kw.lower() in lower)
        if score > 0:
            scored.append((score, entry))
    if not scored:
        return ""
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [e for _, e in scored[:KNOWLEDGE_MATCHES]]
    lines = [
        f"- ({e['attribution']}) {e['summary']}"
        for e in top
    ]
    return "Relevant knowledge (attributed, summarized — not verbatim source material):\n" + "\n".join(lines) + "\n\n"


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


def _explain(result: dict) -> str:
    """Plain-English one-line summary of a task result, derived only from
    real fields already on the result — no fabrication, just readable
    framing of what actually happened."""
    attempts = result.get("attempts")
    attempt_note = f" after {attempts} attempt(s)" if attempts and attempts > 1 else ""

    if result.get("blocked_by") == "zyra":
        return f"Blocked before running: {result.get('reason', 'zyra rejected the task')}."

    if "error" in result and result.get("returncode") is None:
        return f"Failed to run{attempt_note}: {result['error']}."

    rc = result.get("returncode")
    if rc == 0:
        stdout = (result.get("stdout") or "").strip()
        preview = stdout[:160] + ("…" if len(stdout) > 160 else "")
        return f"Completed successfully{attempt_note}. Output: {preview!r}" if preview else f"Completed successfully{attempt_note} with no output."
    elif rc is not None:
        stderr = (result.get("stderr") or "").strip()[:160]
        return f"Exited with error code {rc}{attempt_note}. {('stderr: ' + stderr) if stderr else ''}".strip()
    return "No result recorded."


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
        blocked_result = {"id": task_id, "prompt": prompt, "blocked_by": "zyra", "reason": reason}
        blocked_result["explain"] = _explain(blocked_result)
        (RESULTS_DIR / f"{task_id}.json").write_text(json.dumps(blocked_result, indent=2))
        task_path.rename(PROCESSED_DIR / task_path.name)
        return

    print(f"[run] {task_id}: zyra cleared, dispatching to doug agent", flush=True)
    started = time.time()
    context_prefix = _recent_context()
    knowledge_prefix = _relevant_knowledge(prompt)
    full_prompt = context_prefix + knowledge_prefix + prompt

    max_attempts = 3
    backoff = [0, 2, 5]  # seconds before attempt 1, 2, 3
    attempts_log = []
    result = None
    for attempt in range(1, max_attempts + 1):
        if backoff[attempt - 1]:
            time.sleep(backoff[attempt - 1])
        try:
            proc = subprocess.run(
                [CLAUDE_BIN, "-p", "--agent", "doug", full_prompt],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode == 0:
                result = {
                    "id": task_id,
                    "prompt": prompt,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "duration_seconds": round(time.time() - started, 2),
                    "attempts": attempt,
                }
                print(f"[done] {task_id}: exit=0 in {result['duration_seconds']}s (attempt {attempt})", flush=True)
                break
            attempts_log.append(f"attempt {attempt}: exit={proc.returncode} stderr={proc.stderr[:200]!r}")
            print(f"[retry] {task_id}: attempt {attempt} failed (exit={proc.returncode})", flush=True)
            result = {
                "id": task_id, "prompt": prompt, "returncode": proc.returncode,
                "stdout": proc.stdout, "stderr": proc.stderr,
                "duration_seconds": round(time.time() - started, 2), "attempts": attempt,
            }
        except Exception as e:
            attempts_log.append(f"attempt {attempt}: {type(e).__name__}: {e}")
            print(f"[retry] {task_id}: attempt {attempt} raised ({e})", flush=True)
            result = {
                "id": task_id, "prompt": prompt, "error": f"{type(e).__name__}: {e}",
                "duration_seconds": round(time.time() - started, 2), "attempts": attempt,
            }

    if result.get("returncode") != 0:
        result["attempt_log"] = attempts_log
        print(f"[failed] {task_id}: exhausted {max_attempts} attempts", flush=True)

    result["explain"] = _explain(result)
    print(f"[explain] {task_id}: {result['explain']}", flush=True)

    # Always retire the task file, even on failure — a task must never be
    # left to retry forever and crash-loop the daemon.
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
