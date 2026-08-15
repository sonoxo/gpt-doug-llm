"""
Agent #7 — Community Emergency Mesh (Good Neighbor Agents Track)

Autonomous neighborhood emergency coordinator. Monitors weather alerts,
power outages, and emergency broadcasts. Coordinates neighborhood response:
sends alerts, checks on vulnerable residents, compiles status reports.

Only surfaces the coordinator when resources need allocation decisions.

Free deployment:
  - AWS Lambda + API Gateway (free tier)
  - Twilio free trial ($15 credit, enough for demo)
  - Local machine with cron
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Community Emergency Mesh, an autonomous neighborhood emergency coordinator.

You monitor emergency feeds continuously. When a threat is detected:
1. Send alerts to all registered neighbors via SMS
2. Check on vulnerable residents (elderly, disabled, medical needs)
3. Compile status reports from neighbor responses
4. Identify resource gaps (generators, transportation, medical, food)
5. Only surface the coordinator when resources need allocation decisions

You do NOT make medical decisions. You do NOT dispatch emergency services
(that's 911). You coordinate information and check-ins.
"""


def register_neighbor(name: str, phone: str, needs: list = None, vulnerable: bool = False) -> dict:
    """Register a neighbor in the emergency mesh."""
    import os, json
    registry_path = _PROJECT_ROOT / "hackathon" / "neighborhood_registry.json"
    registry = []
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())
    
    neighbor = {
        "name": name,
        "phone": phone,
        "needs": needs or [],
        "vulnerable": vulnerable,
        "registered_at": __import__("datetime").datetime.now().isoformat(),
    }
    registry.append(neighbor)
    registry_path.write_text(json.dumps(registry, indent=2))
    return {"status": "registered", "name": name, "total_neighbors": len(registry)}


def check_emergency_feeds() -> dict:
    """Check external feeds for emergency indicators.
    
    Uses Zyra Sentinel's external feed monitoring to detect:
    - Weather alerts (via NVD/CISA feed health)
    - Infrastructure threats (satellite feed anomalies)
    - General threat level
    """
    from golden_shield import ZyraSentinel
    
    sentinel = ZyraSentinel()
    external = sentinel.scan_external()
    satellite = sentinel.scan_satellite()
    
    threats = []
    for f in external:
        if f.severity in ("CRITICAL", "HIGH"):
            threats.append({
                "type": "external",
                "severity": f.severity,
                "description": f.description,
                "source": f.source_feed,
            })
    for f in satellite:
        if f.severity == "PLANETARY":
            threats.append({
                "type": "satellite",
                "severity": f.severity,
                "description": f.description,
                "source": f.source_feed,
            })
    
    return {
        "threat_level": "HIGH" if threats else "NORMAL",
        "threat_count": len(threats),
        "threats": threats,
        "needs_coordinator": any(t["severity"] in ("CRITICAL", "PLANETARY") for t in threats),
    }


def coordinate_response(threats: list, neighbors: list = None) -> dict:
    """Coordinate emergency response.
    
    Args:
        threats: List of detected threats
        neighbors: List of registered neighbors
    
    Returns:
        Coordination plan with alerts, check-ins, and resource gaps
    """
    if not neighbors:
        neighbors = []
    
    plan = {
        "alerts_to_send": len(neighbors),
        "vulnerable_checkins": sum(1 for n in neighbors if n.get("vulnerable")),
        "resource_gaps": [],
        "needs_coordinator_decision": False,
    }
    
    # Identify resource gaps
    if threats:
        for t in threats:
            if "power" in t.get("description", "").lower():
                plan["resource_gaps"].append("generators")
            if "food" in t.get("description", "").lower():
                plan["resource_gaps"].append("food")
            if "medical" in t.get("description", "").lower():
                plan["resource_gaps"].append("medical_supplies")
            if "transportation" in t.get("description", "").lower():
                plan["resource_gaps"].append("transportation")
    
    # Surface coordinator if there are gaps
    if plan["resource_gaps"]:
        plan["needs_coordinator_decision"] = True
        plan["coordinator_message"] = (
            f"Emergency detected. {len(threats)} threats. "
            f"Resource gaps identified: {', '.join(plan['resource_gaps'])}. "
            f"Coordinator decision needed for resource allocation."
        )
    
    return plan


if __name__ == "__main__":
    feeds = check_emergency_feeds()
    print(json.dumps(feeds, indent=2))
    if feeds["threat_count"] > 0:
        plan = coordinate_response(feeds["threats"])
        print(json.dumps(plan, indent=2))
