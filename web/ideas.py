"""Idea storage: promotes an agent-chain run's output into a first-class,
persisted "idea" object (title, source task, final output, status), instead
of leaving results buried in ephemeral runs/*.json trace files.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

DIR = os.path.dirname(os.path.abspath(__file__))
IDEAS_FILE = os.path.join(DIR, "ideas.json")
STATUSES = ("draft", "shipped")

_lock = threading.RLock()
_ideas = None


def _load():
    global _ideas
    if _ideas is not None:
        return _ideas
    if os.path.isfile(IDEAS_FILE):
        try:
            with open(IDEAS_FILE) as f:
                _ideas = json.load(f)
                return _ideas
        except (OSError, json.JSONDecodeError):
            pass
    _ideas = {}
    return _ideas


def _save():
    tmp = IDEAS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_ideas, f, indent=2)
    os.replace(tmp, IDEAS_FILE)


def create(title, task, output, owner="operator", run_id=None):
    with _lock:
        data = _load()
        idea_id = uuid.uuid4().hex[:12]
        data[idea_id] = {
            "id": idea_id,
            "title": title[:140],
            "task": task,
            "output": output,
            "status": "draft",
            "owner": owner,
            "run_id": run_id,
            "created_at": time.time(),
            "updated_at": time.time(),
            "worker_status": None,  # None | "processing" | "done" — autonomous worker's own claim marker
        }
        _save()
        return data[idea_id]


def list_all(owner=None, status=None):
    with _lock:
        data = _load()
        items = list(data.values())
        if owner:
            items = [i for i in items if i["owner"] == owner]
        if status:
            items = [i for i in items if i["status"] == status]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)


def get(idea_id):
    with _lock:
        return _load().get(idea_id)


def set_status(idea_id, status):
    if status not in STATUSES:
        raise ValueError(f"invalid status, must be one of {STATUSES}")
    with _lock:
        data = _load()
        if idea_id not in data:
            return None
        data[idea_id]["status"] = status
        data[idea_id]["updated_at"] = time.time()
        _save()
        return data[idea_id]


def claim_next_draft():
    """Atomically claims one unclaimed draft idea for the autonomous
    worker (worker_status None -> "processing"), so two worker ticks (or
    a worker tick racing a manual request) can never double-process the
    same idea. Returns the claimed idea dict, or None if there's nothing
    to do."""
    with _lock:
        data = _load()
        for idea in sorted(data.values(), key=lambda i: i["created_at"]):
            if idea["status"] == "draft" and idea.get("worker_status") is None:
                idea["worker_status"] = "processing"
                idea["updated_at"] = time.time()
                _save()
                return dict(idea)
    return None


def update_output(idea_id, output, run_id, worker_status="done"):
    with _lock:
        data = _load()
        if idea_id not in data:
            return None
        data[idea_id]["output"] = output
        data[idea_id]["run_id"] = run_id
        data[idea_id]["worker_status"] = worker_status
        data[idea_id]["updated_at"] = time.time()
        _save()
        return data[idea_id]
