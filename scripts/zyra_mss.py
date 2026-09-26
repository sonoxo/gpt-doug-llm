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
WIRING = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-max-patent-wiring-v1.json"
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
    print("\nResearch note: targeted sweep only; the exhaustive local corpus reader is a separate path.")


def patent_wiring() -> None:
    w = load(WIRING)
    print("🔗 ZYRA-MSS // GPT-DOUG-MAX PATENT FABRIC")
    print("==========================================")
    print(f"Schema ........... {w['schema']}")
    print(f"Mode ............. {w['mode']}")
    print(f"Components ....... {len(w['components'])}")
    print(f"Links ............ {len(w['links'])}")
    print("\nZYRA-MSS links:")
    for link in w["links"]:
        if "ZYRA_MSS" in (link["from"], link["to"]):
            print(f"  {link['from']} --{link['type']}--> {link['to']}")
    print("\nBoundary ......... advisory research only; consequential actions remain human-authorized")


def doctor() -> int:
    errors: list[str] = []
    try:
        o = load(ONTOLOGY)
        s = load(SWEEP)
        w = load(WIRING)
    except Exception as exc:
        print(f"❌ ZYRA-MSS DOCTOR: invalid/missing JSON: {exc}")
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
    required_wiring = {"GPT_DOUG_MAX", "ZYRA_MSS", "USPTO_PATENT_INTEL", "USPTO_CORPUS_READER", "GLASS_ONION", "HUMAN_REVIEW"}
    missing_wiring = required_wiring - set(w.get("components", {}))
    if missing_wiring:
        errors.append(f"patent wiring incomplete: {sorted(missing_wiring)}")
    if w.get("required_controls", {}).get("automatic_external_action") is not False:
        errors.append("patent fabric automatic external action must be false")
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
    print("   GPT-DOUG-MAX ... wired")
    print("   USPTO corpus ... wired")
    print("   auto external . false")
    print("   human boundary  required")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="zyrapalantir mss")
    p.add_argument("command", nargs="?", default="summary",
                   choices=["summary", "ontology", "agents", "patent-sweep", "patent-wiring", "doctor"])
    a = p.parse_args()
    if a.command == "summary":
        summary(); return 0
    if a.command == "ontology":
        ontology(); return 0
    if a.command == "agents":
        agents(); return 0
    if a.command == "patent-sweep":
        patent_sweep(); return 0
    if a.command == "patent-wiring":
        patent_wiring(); return 0
    if a.command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
