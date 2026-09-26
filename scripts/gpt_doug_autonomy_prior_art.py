#!/usr/bin/env python3
"""Inspect GPT-DOUG adjacent autonomy prior-art watch data.

This is a local research/engineering tool. It performs no network calls,
controls no vehicle, and makes no legal conclusions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/uspto-adjacent-tesla-autonomous-vehicle-summon-family.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/gpt-doug-adjacent-autonomy-prior-art-v1.json"
BRIEF = ROOT / "intel/briefings/2026-09-12-tesla-autonomous-vehicle-summon-prior-art.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summary() -> None:
    source = load_json(SOURCE)
    print("🚘 GPT-DOUG // ADJACENT AUTONOMY PRIOR-ART WATCH")
    print("================================================")
    print(f"Company .......... {source.get('company')}")
    print(f"Family ........... {source.get('family_title')}")
    print(f"Exact documents .. {len(source.get('documents', []))}")
    print(f"Watch ............ {source.get('architecture_watch', {}).get('name')}")
    print("Mode ............. RESEARCH / INDEPENDENT-DESIGN REVIEW")
    print("Real vehicle ctrl . DISABLED")
    print("Weapon targeting . BLOCKED")
    print("Drone-swarm attack BLOCKED")


def family() -> None:
    source = load_json(SOURCE)
    print("📚 Exact USPTO family records")
    print("============================")
    for record in source.get("documents", []):
        date = record.get("publication_date") or record.get("patent_date")
        print(f"\n{record.get('document_number')}  {date}")
        print(f"  application: {record.get('application_number')}")
        print(f"  applicant:   {record.get('applicant', {}).get('name')}")
        if record.get("assignee"):
            print(f"  assignee:    {record.get('assignee', {}).get('name')}")
        if record.get("relationship"):
            print(f"  relation:    {record.get('relationship')}")
        if record.get("prior_publication"):
            print(f"  prior pub:   {record.get('prior_publication')}")


def flow() -> None:
    source = load_json(SOURCE)
    print("🧠 Civilian autonomy architecture watch")
    print("======================================")
    for i, step in enumerate(source.get("visible_flow", []), 1):
        print(f"{i}. {step}")
    print("\nIndependent-design mapping:")
    for item in source.get("architecture_watch", {}).get("gpt_doug_mapping", []):
        print(f"  • {item}")
    print("\nSafety boundary:")
    print("  • destination/path goal only — not hostile targeting")
    print("  • no weapons control or weapons release")
    print("  • no drone-swarm attack control")
    print("  • real-world mobility requires separate human authorization")


def doctor() -> int:
    errors: list[str] = []
    for path in (SOURCE, ONTOLOGY, BRIEF):
        if not path.exists():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"❌ {error}")
        return 1

    source = load_json(SOURCE)
    ontology = load_json(ONTOLOGY)
    expected = {"US-20230176593-A1", "US-11567514-B2", "US-20200257317-A1"}
    actual = {str(x.get("document_number")) for x in source.get("documents", [])}
    if actual != expected:
        errors.append(f"unexpected document family: {sorted(actual)}")
    if source.get("company") != "Tesla, Inc.":
        errors.append("unexpected company attribution")
    controls = source.get("controls", {})
    if controls.get("allow_weapon_targeting_mapping") is not False:
        errors.append("weapon-targeting guard missing")
    if controls.get("allow_weapon_release_or_drone_swarm_control") is not False:
        errors.append("weapon/drone-swarm guard missing")
    if controls.get("require_human_authorization_for_any_real_world_mobility_action") is not True:
        errors.append("human-authorization guard missing")
    blocked = set(ontology.get("governed_actions", {}).get("BLOCK", []))
    for required in {
        "weapon_target_selection",
        "weapons_release",
        "drone_swarm_attack_control",
        "hostile_pursuit_or_engagement",
        "unattended_real_world_vehicle_command",
    }:
        if required not in blocked:
            errors.append(f"ontology block missing: {required}")

    if errors:
        print("❌ AUTONOMY PRIOR-ART DOCTOR FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✅ AUTONOMY PRIOR-ART DOCTOR: GREEN")
    print("   exact docs ..... 3")
    print("   company ........ Tesla, Inc.")
    print("   civilian watch . active")
    print("   real vehicle ... human authorization required")
    print("   targeting ...... blocked")
    print("   weapons ........ blocked")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-autonomy-prior-art")
    parser.add_argument("command", nargs="?", default="summary", choices=["summary", "family", "flow", "json", "doctor"])
    args = parser.parse_args()
    if args.command == "summary":
        summary()
        return 0
    if args.command == "family":
        family()
        return 0
    if args.command == "flow":
        flow()
        return 0
    if args.command == "json":
        print(json.dumps(load_json(SOURCE), indent=2, sort_keys=True))
        return 0
    if args.command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
