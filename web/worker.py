"""Autonomous marketplace worker.

Runs as a background thread inside server.py. Continuously polls for
"draft" ideas nobody has claimed yet, re-runs each one's underlying task
through the full agent_chain (plan -> execute -> [spawn sub-chains as
needed] -> review), replaces the draft's output with the fresh result,
and auto-ships it if the review passed — no human clicks "Run" or "Ship"
for any of it.

Deliberately sequential, not "100 parallel enterprises": provider rate limits
and shared project state need deterministic processing. This processes the real
queue continuously until the host application stops.
"""
from __future__ import annotations

import threading
import time

from agents import agent_chain
from web import ideas

POLL_INTERVAL_S = 15

_state_lock = threading.Lock()
_state = {"running": False, "current_idea_id": None, "processed_count": 0, "last_tick_at": None}


def status():
    with _state_lock:
        return dict(_state)


def _process_one(idea):
    with _state_lock:
        _state["current_idea_id"] = idea["id"]

    trace = agent_chain.run(idea["task"])
    ideas.update_output(idea["id"], trace.get("transcript", ""), trace["run_id"])

    passed = (trace.get("review") or {}).get("passed")
    if passed:
        ideas.set_status(idea["id"], "shipped")

    with _state_lock:
        _state["current_idea_id"] = None
        _state["processed_count"] += 1

    return passed


def _loop():
    with _state_lock:
        _state["running"] = True
    while True:
        with _state_lock:
            _state["last_tick_at"] = time.time()
        idea = ideas.claim_next_draft()
        if idea:
            try:
                _process_one(idea)
            except Exception:
                # Leave worker_status="processing" so a stuck/failed idea
                # doesn't silently vanish from view — it just won't be
                # reclaimed automatically; a human can inspect and requeue.
                with _state_lock:
                    _state["current_idea_id"] = None
        time.sleep(POLL_INTERVAL_S)


def start():
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread
