"""Storage for paid agent-chain task requests — someone pays $1 via
Stripe Checkout, submits a task description, and gets a real agent-chain
result once payment is confirmed via webhook."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(DIR, "paid_tasks.json")
STATUSES = ("pending_payment", "paid", "processing", "done", "failed")

_lock = threading.RLock()
_data = None


def _load():
    global _data
    if _data is not None:
        return _data
    if os.path.isfile(TASKS_FILE):
        try:
            with open(TASKS_FILE) as f:
                _data = json.load(f)
                return _data
        except (OSError, json.JSONDecodeError):
            pass
    _data = {}
    return _data


def _save():
    tmp = TASKS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_data, f, indent=2)
    os.replace(tmp, TASKS_FILE)


def create(task_description):
    with _lock:
        data = _load()
        task_id = uuid.uuid4().hex[:12]
        data[task_id] = {
            "id": task_id,
            "task": task_description,
            "status": "pending_payment",
            "stripe_session_id": None,
            "run_id": None,
            "result": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        _save()
        return dict(data[task_id])


def list_all():
    with _lock:
        data = _load()
        return sorted(data.values(), key=lambda t: t["created_at"], reverse=True)


def get(task_id):
    with _lock:
        item = _load().get(task_id)
        return dict(item) if item else None


def set_session_id(task_id, session_id):
    with _lock:
        data = _load()
        if task_id not in data:
            return None
        data[task_id]["stripe_session_id"] = session_id
        data[task_id]["updated_at"] = time.time()
        _save()
        return dict(data[task_id])


def mark_paid(task_id):
    with _lock:
        data = _load()
        if task_id not in data:
            return None
        if data[task_id]["status"] != "pending_payment":
            return dict(data[task_id])  # already processed — webhook can retry-deliver
        data[task_id]["status"] = "paid"
        data[task_id]["updated_at"] = time.time()
        _save()
        return dict(data[task_id])


def set_status(task_id, status, run_id=None, result=None):
    if status not in STATUSES:
        raise ValueError(f"invalid status, must be one of {STATUSES}")
    with _lock:
        data = _load()
        if task_id not in data:
            return None
        data[task_id]["status"] = status
        if run_id is not None:
            data[task_id]["run_id"] = run_id
        if result is not None:
            data[task_id]["result"] = result
        data[task_id]["updated_at"] = time.time()
        _save()
        return dict(data[task_id])
