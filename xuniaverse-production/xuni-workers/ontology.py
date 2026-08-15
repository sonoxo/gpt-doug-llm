"""
xuniaverse ontology layer — a Foundry-inspired pattern (Object Types, Link
Types, Action Types) implemented against our own real data. Not connected
to Palantir Foundry — there's no live Foundry tenant/API in this project,
only a Palantir Learn training cert, which grants no API access. This
borrows the *pattern*: a shared semantic model that different consumers
read from and act through, per xuni-workers/knowledge/palantir-*.jsonl.

Object types here are backed by real files already on disk:
  - Task        <- xuni-workers/{tasks,processed}/*.json
  - Result      <- xuni-workers/results/*.json
  - KnowledgeEntry <- xuni-workers/knowledge/*.jsonl

Link types (computed from real fields, not fabricated):
  - Task --produced--> Result        (same task id)
  - Task --referenced--> KnowledgeEntry (keyword overlap, same scoring
    zyra/agent-daemon already use for retrieval)

Action types are typed, validated operations — mirroring Foundry's
"Action" concept — that go through the same Zyra guard the daemon uses,
so the ontology layer can't be used to bypass safety review.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "xuni-workers" / "tasks"
PROCESSED_DIR = ROOT / "xuni-workers" / "processed"
RESULTS_DIR = ROOT / "xuni-workers" / "results"
KNOWLEDGE_DIR = ROOT / "xuni-workers" / "knowledge"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zyra_guard  # noqa: E402


# --- Object types -----------------------------------------------------

def _read_json_safe(path: Path):
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def list_tasks() -> list:
    """Object type: Task. Properties: id, prompt, source dir (queued/processed)."""
    objs = []
    for d, status in ((TASKS_DIR, "queued"), (PROCESSED_DIR, "processed")):
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json")):
            data = _read_json_safe(path)
            if not data:
                continue
            objs.append({
                "object_type": "Task",
                "id": data.get("id", path.stem),
                "prompt": data.get("prompt"),
                "status": status,
            })
    return objs


def list_results() -> list:
    """Object type: Result. Properties from the daemon's actual result files."""
    objs = []
    if not RESULTS_DIR.exists():
        return objs
    for path in sorted(RESULTS_DIR.glob("*.json")):
        data = _read_json_safe(path)
        if not data:
            continue
        objs.append({
            "object_type": "Result",
            "id": data.get("id", path.stem),
            "returncode": data.get("returncode"),
            "blocked_by": data.get("blocked_by"),
            "explain": data.get("explain"),
            "attempts": data.get("attempts"),
        })
    return objs


def list_knowledge() -> list:
    """Object type: KnowledgeEntry. Loaded from xuni-workers/knowledge/*.jsonl."""
    objs = []
    if not KNOWLEDGE_DIR.exists():
        return objs
    for path in sorted(KNOWLEDGE_DIR.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            objs.append({"object_type": "KnowledgeEntry", **entry})
    return objs


# --- Link types ---------------------------------------------------------

def link_task_to_result(task_id: str) -> dict:
    """Task --produced--> Result. Real lookup, not fabricated: returns None
    fields if no result file exists yet."""
    path = RESULTS_DIR / f"{task_id}.json"
    data = _read_json_safe(path) if path.exists() else None
    return {"link_type": "produced", "from": ("Task", task_id), "to": ("Result", task_id) if data else None}


def link_task_to_knowledge(task_id: str, prompt: str, top_n: int = 3) -> list:
    """
    Task --referenced--> KnowledgeEntry, scored by the same keyword-overlap
    logic agent-daemon._relevant_knowledge already uses for real retrieval,
    plus a normalized confidence score:

        confidence = matched_keywords / total_keywords_on_entry, capped at 1.0

    This is a real, deterministic ratio — not a fabricated probability. An
    entry where every one of its keywords appears in the prompt gets 1.0;
    one where only a third of its keywords match gets ~0.33. It measures
    coverage of that entry's own keyword set, not a claim about semantic
    correctness.
    """
    entries = list_knowledge()
    lower = prompt.lower()
    scored = []
    for e in entries:
        keywords = e.get("keywords", [])
        if not keywords:
            continue
        matched = sum(1 for kw in keywords if kw.lower() in lower)
        if matched > 0:
            confidence = min(matched / len(keywords), 1.0)
            scored.append((matched, confidence, e))
    scored.sort(key=lambda triple: (triple[0], triple[1]), reverse=True)
    return [
        {
            "link_type": "referenced",
            "from": ("Task", task_id),
            "to": ("KnowledgeEntry", e["id"]),
            "matched_keywords": m,
            "confidence": round(c, 3),
        }
        for m, c, e in scored[:top_n]
    ]


# --- Action types ---------------------------------------------------------

class ActionValidationError(Exception):
    pass


def submit_task_action(task_id: str, prompt: str) -> dict:
    """
    Action type: SubmitTask.
    Parameters: task_id (str), prompt (str).
    Validation: routed through zyra_guard.review — the same gate the daemon
    uses — so this action type can't be used to bypass safety review.
    Effect: writes a real task file to xuni-workers/tasks/, exactly what the
    running daemon already watches and picks up.
    """
    if not task_id or not isinstance(task_id, str):
        raise ActionValidationError("task_id must be a non-empty string")
    if not prompt or not isinstance(prompt, str):
        raise ActionValidationError("prompt must be a non-empty string")

    allowed, reason = zyra_guard.review({"id": task_id, "prompt": prompt})
    if not allowed:
        raise ActionValidationError(f"rejected by zyra_guard: {reason}")

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    task_path = TASKS_DIR / f"{task_id}.json"
    task_path.write_text(json.dumps({"id": task_id, "prompt": prompt, "source": "ontology.submit_task_action"}))
    return {"action": "SubmitTask", "status": "submitted", "task_id": task_id, "path": str(task_path)}


# --- Ontology summary -------------------------------------------------

def summary() -> dict:
    tasks = list_tasks()
    results = list_results()
    knowledge = list_knowledge()
    links = []
    for t in tasks:
        links.append(link_task_to_result(t["id"]))
        links.extend(link_task_to_knowledge(t["id"], t["prompt"] or ""))
    return {
        "object_counts": {"Task": len(tasks), "Result": len(results), "KnowledgeEntry": len(knowledge)},
        "link_count": len([l for l in links if l.get("to")]),
    }


SNAPSHOT_PATH = ROOT / "xuni-workers" / "live" / "ontology-snapshot.json"


def write_snapshot() -> dict:
    """Persist the live summary with a timestamp so counts are auditable
    over time, not just computed on demand."""
    import time
    data = summary()
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(data, indent=2))
    return data


if __name__ == "__main__":
    print(json.dumps(write_snapshot(), indent=2))
