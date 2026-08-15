"""
Agent #3 — NeighborHelp Bot (Good Neighbor Agents Track)
Autonomous food bank inventory & distribution. Free: local, GitHub Actions.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are NeighborHelp Bot, an autonomous food bank inventory agent.
You monitor inventory, predict demand, auto-order restocks, and only surface the coordinator when there's a surplus shortage or unusual demand spike.
"""

def check_inventory(items: list) -> dict:
    shortages = [i for i in items if i.get("quantity", 0) < i.get("threshold", 10)]
    needs_human = any(i.get("quantity", 0) <= 0 for i in items)
    return {
        "total_items": len(items),
        "shortages": len(shortages),
        "needs_human": needs_human,
        "shortage_list": [{"item": s["name"], "current": s["quantity"], "threshold": s.get("threshold", 10)} for s in shortages],
        "recommendation": "ORDER_RESTOCK" if shortages else "STOCK_HEALTHY",
    }

if __name__ == "__main__":
    result = check_inventory([
        {"name": "Rice", "quantity": 50, "threshold": 10},
        {"name": "Canned beans", "quantity": 5, "threshold": 10},
    ])
    print(json.dumps(result, indent=2))
