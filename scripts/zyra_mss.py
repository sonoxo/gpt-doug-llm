#!/usr/bin/env python3
"""ZYRA-MSS local mission-support architecture CLI.

This command validates and explains the bounded ZYRA-MSS architecture. It does
not perform network crawling, targeting, weapons control, or unattended real-
world actions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "safety-shield" / "ontology" / "zyra-mss-v1.json"
SWEEP = ROOT / "intel" / "sources" / "zyra-mss-patent-architecture-sweep-2026-09-12.json"
DOC = ROOT / "docs" / "ZYRA_MSS.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summary() -> None:
    o = load(ONTOLOGY)
    fleet = o["logical_agent_fleet"]
    print("🧠 ZYRA-MSS // MISSION SUPPORT SYSTEM")
    print("=====================================")
    print(f"Mode ............. {o['mode']}")
    print(f"Ontology ......... {o['ontology']}")
    print(f"Logical workers .. {fleet['count']}")
    print(f"Authority ........ {fleet['agent_authority']}")
    print(f"Auto external .... {str(fleet['automatic_external_action']).lower()}")
    print(f"Policy engine .... {o['control_plane']['policy_engine']}")
    print(f"Supply chain ..... {o['control_plane']['software_assurance']}")
    print(f"Supervisor ....... {o['control_plane']['runtime_supervisor']}")
    print(f"Human boundary ... {o['control_plane']['decision_boundary']}")
    print("\nDomains:")
    for d in o["mission_support_domains"]:
        print(f"  • {d}")


def agents() -> None:
    fleet = load(ONTOLOGY)["logical_agent_fleet"]
    print("🤖 ZYRA-MSS // 100-WORKER LOGICAL SWARM")
    print("=======================================")
    for span, role in fleet["roles"].items():
        print(f"{span:>5}  {role}")
    print(f"\nNetwork cap ...... {fleet['network_concurrency_cap']}")
    print(f"Agent authority .. {fleet['agent_authority']}")
    print("External action .. HUMAN AUTHORIZATION REQUIRED")


def ontology() -> None:
    o = load(ONTOLOGY)
    print(json.dumps({
        "ontology": o["ontology"],
        "object_types": o["object_types"],
        "link_types": o["link_types"],
        "readiness_gate": o["readiness_gate"],
        "governed_actions": o["governed_actions"],
    }, indent=2, sort_keys=True))


def patent_sweep() -> None:
    s = load(SWEEP)
    print("🔎 ZYRA-MSS // PUBLIC PATENT ARCHITECTURE SWEEP")
    print("================================================")
    print(f"Primary source ... {s['primary_source']}")
    print(f"Signals .......... {len(s['architecture_signals'])}")
    print(f"Logical agents ... {s['research_method']['logical_agent_count']}")
    print(f"Network cap ...... {s['research_method']['network_concurrency_cap']}")
    print("\nSelected architecture signals:")
    for item in s["architecture_signals"]:
        print(f"  {item['document']:<20} {item['theme']}")
    print("\nResearch note: targeted sweep only; not a complete read of every USPTO PDF.")


def doctor() -> int:
    errors: list[str] = []
    try:
        o = load(ONTOLOGY)
        s = load(SWEEP)
    except Exception as exc:
        print(f"❌ ZYRA-MSS DOCTOR: invalid JSON: {exc}")
        return 1

    if o.get("ontology") != "ZYRA_MSS_V1":
        errors.append("unexpected ontology id")
    if o.get("logical_agent_fleet", {}).get("count") != 100:
        errors.append("logical agent count must be 100")
    if o.get("logical_agent_fleet", {}).get("automatic_external_action") is not False:
        errors.append("automatic external action must be false")
    blocked = set(o.get("governed_actions", {}).get("BLOCK", []))
    required_blocks = {
        "autonomous_target_selection",
        "weapons_release",
        "weapon_or_drone_swarm_control",
        "hostile_engagement",
        "critical_infrastructure_disruption",
        "unattended_real_world_vehicle_command",
        "bypass_human_authorization",
    }
    if not required_blocks.issubset(blocked):
        errors.append("safety block set incomplete")
    if s.get("research_method", {}).get("network_concurrency_cap", 999) > 8:
        errors.append("research network concurrency cap too high")
    if not DOC.exists():
        errors.append("ZYRA_MSS.md missing")

    if errors:
        print("❌ ZYRA-MSS DOCTOR FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("✅ ZYRA-MSS DOCTOR: GREEN")
    print(f"   ontology ....... {o['ontology']}")
    print(f"   object types ... {len(o['object_types'])}")
    print(f"   link types ..... {len(o['link_types'])}")
    print(f"   logical agents . {o['logical_agent_fleet']['count']}")
    print(f"   patent signals . {len(s['architecture_signals'])}")
    print("   auto external . false")
    print("   human boundary  required")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="zyrapalantir mss")
    p.add_argument("command", nargs="?", default="summary",
                   choices=["summary", "ontology", "agents", "patent-sweep", "doctor"])
    a = p.parse_args()
    if a.command == "summary":
        summary(); return 0
    if a.command == "ontology":
        ontology(); return 0
    if a.command == "agents":
        agents(); return 0
    if a.command == "patent-sweep":
        patent_sweep(); return 0
    if a.command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
