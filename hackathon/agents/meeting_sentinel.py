"""
Agent #4 — Zyra Meeting Sentinel (Everyday Agents Track)
Autonomous calendar conflict resolver. Free: Google Calendar API (free), local.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Zyra Meeting Sentinel, an autonomous calendar manager.
You watch the calendar. When a meeting request arrives:
1. Check for conflicts
2. Propose alternatives based on preferences
3. Auto-accept/reject based on rules
4. Only surface when there's an ambiguous conflict needing human judgment
"""

def check_conflict(new_meeting: dict, existing: list) -> dict:
    from datetime import datetime
    new_start = datetime.fromisoformat(new_meeting["start"])
    new_end = datetime.fromisoformat(new_meeting["end"])
    conflicts = []
    for m in existing:
        m_start = datetime.fromisoformat(m["start"])
        m_end = datetime.fromisoformat(m["end"])
        if new_start < m_end and new_end > m_start:
            conflicts.append(m)
    return {"has_conflict": bool(conflicts), "conflicts": conflicts, "needs_human": len(conflicts) > 1}

if __name__ == "__main__":
    result = check_conflict(
        {"title": "Demo", "start": "2026-09-01T10:00:00", "end": "2026-09-01T11:00:00"},
        [{"title": "Standup", "start": "2026-09-01T09:30:00", "end": "2026-09-01T10:15:00"}]
    )
    print(json.dumps(result, indent=2))
