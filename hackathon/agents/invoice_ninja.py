"""
Agent #6 — Zyra Invoice Ninja (Professional Agents Track)

Autonomous freelancer invoice & payment chaser. Generates invoices,
sends them, follows up on overdue payments with escalating reminders.

Free deployment:
  - GitHub Actions cron (free for public repos)
  - AWS Lambda free tier
  - Local cron + Stripe API (existing integration)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Zyra Invoice Ninja, an autonomous freelancer invoice and payment agent.

You handle the full invoice cycle:
1. Generate invoices from tracked hours
2. Send invoices to clients via email
3. Follow up on overdue payments with escalating reminders:
   - Day 1 overdue: friendly reminder
   - Day 7: firm reminder with late fee notice
   - Day 14: final notice with collections warning
4. Process payments via Stripe (existing integration)
5. Only surface the freelancer when:
   - A client disputes an invoice
   - A payment fails
   - A client hasn't responded after 14 days
"""


def generate_invoice(client: str, hours: float, rate: float, description: str = "") -> dict:
    """Generate an invoice."""
    amount = hours * rate
    invoice = {
        "client": client,
        "hours": hours,
        "rate": rate,
        "amount": amount,
        "description": description,
        "status": "draft",
    }
    return invoice


def check_overdue_invoices(invoices: list) -> dict:
    """Check for overdue invoices and determine follow-up actions."""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    actions = []
    
    for inv in invoices:
        if inv.get("status") != "sent":
            continue
        sent_date = datetime.fromisoformat(inv.get("sent_date", now.isoformat()))
        days_overdue = (now - sent_date).days
        
        if days_overdue <= 0:
            continue
        elif days_overdue == 1:
            actions.append({"invoice": inv["client"], "action": "friendly_reminder", "days_overdue": days_overdue})
        elif days_overdue == 7:
            actions.append({"invoice": inv["client"], "action": "firm_reminder", "days_overdue": days_overdue, "late_fee": True})
        elif days_overdue == 14:
            actions.append({"invoice": inv["client"], "action": "final_notice", "days_overdue": days_overdue, "collections_warning": True})
        elif days_overdue > 14:
            actions.append({"invoice": inv["client"], "action": "surface_freelancer", "days_overdue": days_overdue, "reason": "client unresponsive after 14 days"})
    
    needs_human = any(a["action"] == "surface_freelancer" for a in actions)
    return {
        "overdue_count": len(actions),
        "actions": actions,
        "needs_human": needs_human,
    }


if __name__ == "__main__":
    inv = generate_invoice("Acme Corp", 40, 75, "Backend development")
    print(json.dumps(inv, indent=2))
    overdue = check_overdue_invoices([{
        "client": "Acme Corp",
        "status": "sent",
        "sent_date": "2026-07-15T00:00:00",
    }])
    print(json.dumps(overdue, indent=2))
