"""
Agent #9 — Zyra Expense Sentinel (Everyday Agents Track)
Autonomous receipt scanner & expense categorizer. Free: Gmail API (free), local.
"""
from __future__ import annotations
import json, sys, re
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Zyra Expense Sentinel, an autonomous expense tracker.
You watch email for receipts, extract amount/merchant/date/category, track budget, flag anomalies.
Only surface when there's an unusual charge or budget threshold exceeded.
Zyra redacts all financial data from agent logs.
"""

CATEGORIES = {
    "amazon": "shopping", "uber": "transport", "lyft": "transport",
    "starbucks": "food", "mcdonalds": "food", "whole foods": "groceries",
    "netflix": "entertainment", "spotify": "entertainment",
    "shell": "gas", "chevron": "gas", "att": "utilities", "comcast": "utilities",
}

def categorize_expense(merchant: str, amount: float) -> dict:
    merchant_lower = merchant.lower()
    category = "other"
    for key, cat in CATEGORIES.items():
        if key in merchant_lower:
            category = cat
            break
    return {"merchant": merchant, "amount": amount, "category": category}

def check_budget(expenses: list, budget: dict) -> dict:
    from collections import defaultdict
    totals = defaultdict(float)
    for e in expenses:
        totals[e["category"]] += e["amount"]
    over_budget = {cat: amt for cat, amt in totals.items() if amt > budget.get(cat, float('inf'))}
    return {
        "total_spent": sum(totals.values()),
        "by_category": dict(totals),
        "over_budget": over_budget,
        "needs_human": bool(over_budget),
    }

if __name__ == "__main__":
    exp = categorize_expense("Amazon", 49.99)
    print(json.dumps(exp, indent=2))
    budget = check_budget([exp, {"category": "food", "amount": 200}], {"food": 150, "shopping": 100})
    print(json.dumps(budget, indent=2))
