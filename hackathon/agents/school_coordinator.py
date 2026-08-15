"""
Agent #10 — Doug School Coordinator (Good Neighbor Agents Track)
Autonomous school volunteer & event coordinator. Free: local, Twilio free trial.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Doug School Coordinator, an autonomous PTA volunteer coordinator.
You match volunteers to roles, send reminders, track hours, coordinate event logistics.
Only surface the coordinator when there's a gap needing human recruitment.
"""

def match_volunteers(roles: list, volunteers: list) -> dict:
    matches = []
    unfilled = []
    for role in roles:
        matched = False
        for v in volunteers:
            if any(skill in role.get("required_skills", []) for skill in v.get("skills", [])):
                if v.get("available", True):
                    matches.append({"role": role["name"], "volunteer": v["name"]})
                    v["available"] = False
                    matched = True
                    break
        if not matched:
            unfilled.append(role)
    return {
        "filled": len(matches),
        "unfilled": len(unfilled),
        "matches": matches,
        "needs_human": bool(unfilled),
        "unfilled_roles": [{"role": r["name"], "skills": r.get("required_skills", [])} for r in unfilled],
    }

if __name__ == "__main__":
    result = match_volunteers(
        [{"name": "Setup", "required_skills": ["lifting"]}, {"name": "Food server", "required_skills": ["cooking"]}],
        [{"name": "Alice", "skills": ["lifting", "cooking"], "available": True}, {"name": "Bob", "skills": ["music"], "available": True}]
    )
    print(json.dumps(result, indent=2))
