from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from va3lm.agents import roster


def build_plan(goal: str) -> dict:
    clean = goal.strip()
    if not clean:
        raise ValueError("goal is required")
    plan_id = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
    steps = [
        {"order": 1, "agent": "architect", "action": "design", "state": "READY"},
        {"order": 2, "agent": "coder", "action": "propose-change", "state": "READY"},
        {"order": 3, "agent": "ontology", "action": "link-artifacts", "state": "READY"},
        {"order": 4, "agent": "tester", "action": "validate", "state": "READY"},
        {"order": 5, "agent": "security", "action": "security-review", "state": "READY"},
        {"order": 6, "agent": "reviewer", "action": "quality-review", "state": "READY"},
        {"order": 7, "agent": "explainer", "action": "create-explainer", "state": "READY"},
        {"order": 8, "agent": "commander", "action": "request-human-approval", "state": "BLOCKED_PENDING_APPROVAL"},
        {"order": 9, "agent": "evidence", "action": "record-build-evidence", "state": "WAITING"},
    ]
    return {
        "planId": plan_id,
        "goal": clean,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "brain": "gpt-doug-llm",
        "agents": [item["id"] for item in roster()],
        "steps": steps,
        "mutationGate": "HUMAN_APPROVAL_REQUIRED",
    }
