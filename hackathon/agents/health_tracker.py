"""
Agent #5 — Doug Health Tracker (Everyday Agents Track)
Autonomous medication & appointment manager. Free: Twilio free trial, local.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Doug Health Tracker, an autonomous medication and appointment manager.
You track schedules, remind at the right time, auto-book refills, schedule appointments.
Only surface when there's a drug interaction warning or appointment conflict.
You do NOT give medical advice — just logistics. Zyra redacts all health data from logs.
"""

def check_schedule(medications: list) -> dict:
    now = __import__("datetime").datetime.now()
    reminders = []
    for med in medications:
        if med.get("next_dose") and med.get("next_dose") <= now.isoformat():
            reminders.append({"medication": med["name"], "action": "take_now", "next_refill": med.get("refill_date")})
    needs_human = any(r.get("next_refill") and r["next_refill"] <= now.isoformat() for r in reminders)
    return {"reminders": reminders, "needs_human": needs_human}

if __name__ == "__main__":
    result = check_schedule([{"name": "Lisinopril", "next_dose": "2026-01-01T08:00:00", "refill_date": "2026-01-15"}])
    print(json.dumps(result, indent=2))
