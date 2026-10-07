#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "ecosystem" / "registry.v4.json"
AI_MANIFEST = ROOT / "config" / "ai-layer-manifest.json"

sys.path.insert(0, str(ROOT))

from hivemind.capabilities import doctor as capability_doctor  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(registry: dict, ai: dict) -> None:
    required = {
        "ecosystem_version",
        "canonical_control_root",
        "canonical_hub",
        "domain_registry",
        "execution_plane",
        "core_planes",
        "canonical_flow",
        "domain_routing",
        "architecture_rules",
    }
    missing = sorted(required - registry.keys())
    if missing:
        raise SystemExit(f"ECO FABRIC NO-GO: registry missing {', '.join(missing)}")

    planes = registry["core_planes"]
    plane_ids = [p.get("id") for p in planes]
    if len(plane_ids) != len(set(plane_ids)):
        raise SystemExit("ECO FABRIC NO-GO: duplicate core plane IDs")
    if any(not p.get("repo") or not p.get("role") for p in planes):
        raise SystemExit("ECO FABRIC NO-GO: incomplete core plane")

    known = set(plane_ids) | {d.get("id") for d in registry.get("internal_divisions", [])}
    for domain, target in registry["domain_routing"].items():
        if target not in known:
            raise SystemExit(f"ECO FABRIC NO-GO: route {domain!r} -> unknown target {target!r}")

    required_layers = set(ai.get("required_layer_ids", []))
    declared_layers = {x.get("id") for x in ai.get("layers", [])}
    if required_layers != declared_layers:
        raise SystemExit("ECO FABRIC NO-GO: AI layer contract mismatch")


def build_snapshot() -> dict:
    registry = load_json(REGISTRY)
    ai = load_json(AI_MANIFEST)
    validate_registry(registry, ai)

    caps = capability_doctor()
    integrations = [c.to_dict() for c in caps]
    available = sum(1 for c in integrations if c["available"])
    required_missing = [c["slug"] for c in integrations if c["required"] and not c["available"]]

    planes = []
    for p in registry["core_planes"]:
        planes.append(
            {
                "id": p["id"],
                "label": p["label"],
                "repo": p["repo"],
                "role": p["role"],
                "responsibilities": p.get("responsibilities", []),
                "state": "DECLARED",
            }
        )

    return {
        "schema": "xunia.maven.eco-fabric.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ecosystem": {
            "name": registry["name"],
            "version": registry["ecosystem_version"],
            "control_root": registry["canonical_control_root"],
            "hub": registry["canonical_hub"],
            "domain_registry": registry["domain_registry"],
            "execution_plane": registry["execution_plane"],
            "canonical_flow": registry["canonical_flow"],
        },
        "summary": {
            "core_planes": len(planes),
            "internal_divisions": len(registry.get("internal_divisions", [])),
            "research_satellites": len(registry.get("research_satellites", [])),
            "ai_layers": len(ai.get("layers", [])),
            "integrations_total": len(integrations),
            "integrations_available": available,
            "required_integrations_missing": required_missing,
            "runtime_state": "DEGRADED" if required_missing else "READY",
        },
        "planes": planes,
        "domain_routing": registry["domain_routing"],
        "internal_divisions": registry.get("internal_divisions", []),
        "research_satellites": registry.get("research_satellites", []),
        "ai_layers": ai.get("layers", []),
        "integrations": integrations,
        "architecture_rules": registry["architecture_rules"],
        "authority": {
            "model_output_creates_execution_authority": False,
            "repository_membership_creates_external_authorization": False,
            "human_review_required_for_consequential_release": True,
            "public_source_state_must_remain_distinct_from_inference": True,
        },
    }


def write_snapshot(out: Path) -> dict:
    snap = build_snapshot()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    return snap


def print_status(snap: dict) -> None:
    s = snap["summary"]
    print("🌐 GPT-DOUG // MAVEN ECO FABRIC")
    print("=" * 58)
    print("ECOSYSTEM .........", snap["ecosystem"]["version"])
    print("CONTROL ROOT ......", snap["ecosystem"]["control_root"])
    print("CORE PLANES .......", s["core_planes"])
    print("AI LAYERS .........", s["ai_layers"])
    print("INTEGRATIONS ......", f"{s['integrations_available']}/{s['integrations_total']} available")
    print("RUNTIME ...........", s["runtime_state"])
    if s["required_integrations_missing"]:
        print("REQUIRED MISSING ..", ", ".join(s["required_integrations_missing"]))
    print("AUTHORITY ......... HUMAN-GOVERNED")


def cmd_doctor() -> None:
    snap = build_snapshot()
    assert snap["schema"] == "xunia.maven.eco-fabric.v1"
    assert snap["ecosystem"]["control_root"] == "sonoxo/gpt-doug-llm"
    assert snap["authority"]["model_output_creates_execution_authority"] is False
    assert snap["authority"]["repository_membership_creates_external_authorization"] is False
    assert len({p["id"] for p in snap["planes"]}) == len(snap["planes"])
    print("✅ MAVEN ECO FABRIC DOCTOR: GREEN")
    print_status(snap)


def main() -> None:
    parser = argparse.ArgumentParser(description="GPT-DOUG MAVEN ECO FABRIC runtime snapshot")
    sub = parser.add_subparsers(dest="command", required=True)

    s_snapshot = sub.add_parser("snapshot")
    s_snapshot.add_argument("--out", required=True)

    sub.add_parser("status")
    sub.add_parser("doctor")

    args = parser.parse_args()

    if args.command == "snapshot":
        snap = write_snapshot(Path(args.out).expanduser())
        print_status(snap)
        print("SNAPSHOT ..........", Path(args.out).expanduser())
    elif args.command == "status":
        print_status(build_snapshot())
    elif args.command == "doctor":
        cmd_doctor()


if __name__ == "__main__":
    main()
