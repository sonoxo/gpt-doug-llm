#!/usr/bin/env python3
"""GPT-DOUG-MAX patent-aware robotics schematic and compliance lab.

Generates high-level engineering schematic packages for civilian/industrial robotics
and programmable devices using public patent evidence as a prior-art signal while
failing closed on unknown jurisdictions and preserving human legal/safety review.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-max-robotics-compliance-v1.json"
PATENT_SEED = ROOT / "safety-shield" / "agents" / "knowledge" / "patents" / "us-12697722-b2-robot-mission-seed.json"
DEFAULT_OUTPUT_ROOT = ROOT / "build" / "robotics-schematics"

PRODUCT_CLASSES = {
    "programmable-device",
    "industrial-robot",
    "collaborative-robot",
    "mobile-robot",
    "personal-care-robot",
    "lab-robot",
}
DENIED_TERMS = {
    "weapon",
    "weapons",
    "fire-control",
    "fire control",
    "targeting",
    "autonomous engagement",
    "munition",
    "missile",
}


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"NO-GO: required file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"NO-GO: invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"NO-GO: expected object in {path}")
    return data


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "design"


def check_scope(name: str, description: str) -> None:
    haystack = f"{name} {description}".lower()
    blocked = sorted(term for term in DENIED_TERMS if term in haystack)
    if blocked:
        raise SystemExit(
            "NO-GO: this schematic lab is scoped to civilian/industrial programmable devices; "
            f"blocked capability term(s): {', '.join(blocked)}"
        )


def normalize_jurisdictions(raw: list[str], registry: dict) -> list[str]:
    known = registry.get("jurisdictions", {})
    values: list[str] = []
    for entry in raw or ["US"]:
        code = entry.strip().upper()
        if code not in known:
            raise SystemExit(
                f"NO-GO: jurisdiction {code!r} has no validated pack. "
                "Add an official-source jurisdiction pack and human-review it before release."
            )
        if code not in values:
            values.append(code)
    return values


def standards_for(product_class: str) -> list[str]:
    base = ["ISO-12100", "ISO-13849-1", "IEC-60204-1", "IEC-61508", "IEC-62443"]
    if product_class in {"industrial-robot", "collaborative-robot", "mobile-robot", "lab-robot"}:
        base.append("ISO-10218-1/2")
    if product_class == "collaborative-robot":
        base.append("ISO-TS-15066")
    if product_class == "personal-care-robot":
        base.append("ISO-13482")
    return base


def compliance_matrix(
    registry: dict,
    jurisdictions: list[str],
    product_class: str,
    flags: dict[str, bool],
) -> list[dict]:
    rows: list[dict] = []
    baseline = {x.get("id"): x for x in registry.get("global_engineering_baseline", []) if isinstance(x, dict)}
    for standard_id in standards_for(product_class):
        item = baseline.get(standard_id, {"id": standard_id, "topic": "engineering safety standard"})
        rows.append(
            {
                "scope": "GLOBAL_ENGINEERING_BASELINE",
                "authority": "consensus-standard ecosystem",
                "requirement": standard_id,
                "topic": item.get("topic", ""),
                "status": "APPLICABILITY_REVIEW",
                "mandatory": False,
                "source": item.get("source"),
            }
        )

    for code in jurisdictions:
        pack = registry["jurisdictions"][code]
        for rule in pack.get("rules", []):
            trigger = str(rule.get("trigger", "")).lower()
            conditional = False
            if "radio" in trigger or "wireless" in trigger or "radio-frequency" in trigger:
                conditional = not flags.get("wireless", False)
            elif "ai " in trigger or trigger.startswith("ai") or "ai-enabled" in trigger:
                conditional = not flags.get("ai", False)
            elif "export" in trigger:
                conditional = not flags.get("export", False)
            if conditional:
                continue
            rows.append(
                {
                    "scope": code,
                    "authority": ", ".join(pack.get("authorities", [])),
                    "requirement": rule.get("id"),
                    "topic": rule.get("topic"),
                    "trigger": rule.get("trigger"),
                    "status": rule.get("status", "APPLICABILITY_REVIEW"),
                    "mandatory": rule.get("type") in {"regulation", "directive", "export_control"},
                    "source": rule.get("source"),
                }
            )

        for sector, enabled in flags.items():
            if not enabled:
                continue
            sector_info = registry.get("sector_triggers", {}).get(sector)
            if sector_info:
                rows.append(
                    {
                        "scope": code,
                        "authority": "sector regulator review required",
                        "requirement": f"SECTOR:{sector.upper()}",
                        "topic": "; ".join(sector_info.get("review", [])),
                        "status": "HUMAN_APPLICABILITY_REVIEW",
                        "mandatory": None,
                        "source": None,
                    }
                )
    return rows


def architecture_mermaid(product_class: str, ai_enabled: bool) -> str:
    ai_node = "  SYN[Independent Pattern Synthesizer]\n  CTX --> SYN\n  EVID --> SYN\n  SYN --> COMP\n" if ai_enabled else "  RULES[Deterministic Pattern Rules]\n  CTX --> RULES\n  EVID --> RULES\n  RULES --> COMP\n"
    return f"""flowchart LR
  HUMAN[Operator / Engineer] --> TASK[Robot-Agnostic Task Contract]
  TASK --> CTX[Context + Requirements Model]
  PAT[Public Patent / Prior-Art Evidence] --> EVID[Provenance Store]
{ai_node}  COMP[Patent Boundary + Compliance Gate]
  COMP --> RISK[Hazard / Risk Review]
  RISK --> PLAN[Mission / Device Planner]
  PLAN --> APPROVE[Human Approval Gate]
  APPROVE --> ADAPT[Device Abstraction Layer]
  ADAPT --> CTRL[Safety-Supervised Runtime]
  CTRL --> DEVICE[{product_class}]
  DEVICE --> TELEMETRY[Telemetry + Audit]
  TELEMETRY --> CTX
  ESTOP[Emergency Stop / Safe-State Input] --> CTRL
"""


def electrical_mermaid(product_class: str) -> str:
    return f"""flowchart LR
  PWRIN[Power Input] --> PROTECT[Input Protection / Isolation]
  PROTECT --> LV[Regulated Low-Voltage Rails]
  LV --> COMPUTE[Main Compute]
  LV --> SAFE[Independent Safety Controller]
  LV --> SENSORS[Authorized Sensors]
  COMPUTE --> BUS[Device / Field Bus]
  SENSORS --> COMPUTE
  BUS --> DRIVER[Actuator Driver]
  SAFE --> INTERLOCK[Hardware / Safety Interlock]
  ESTOP[Emergency Stop / Guard Inputs] --> SAFE
  INTERLOCK --> DRIVER
  DRIVER --> ACT[Actuators for {product_class}]
  COMPUTE --> LOG[Audit / Diagnostics]
  SAFE --> LOG
"""


def software_mermaid(ai_enabled: bool) -> str:
    planner = "AI-assisted independent planner" if ai_enabled else "deterministic planner"
    return f"""flowchart TD
  INPUT[Human-readable task] --> VALIDATE[Task Schema Validation]
  VALIDATE --> CONTEXT[Context Acquisition]
  CONTEXT --> PRIORART[Prior-Art Retrieval + Provenance]
  PRIORART --> DESIGN[{planner}]
  DESIGN --> PATENT[Patent Boundary Check]
  PATENT --> COMPLIANCE[Jurisdiction / Agency Preflight]
  COMPLIANCE --> RISK[Safety Risk Controls]
  RISK --> HUMAN[Human Release Approval]
  HUMAN --> ADAPTER[Vendor / Device Adapter]
  ADAPTER --> RUNTIME[Safety-Supervised Runtime]
  RUNTIME --> AUDIT[Telemetry / Immutable Decision Record]
"""


def design_controls(product_class: str, flags: dict[str, bool]) -> list[dict]:
    controls = [
        {"id": "CTRL-001", "control": "hazard analysis before energizing actuators", "gate": "required"},
        {"id": "CTRL-002", "control": "manual override and safe-state transition", "gate": "required"},
        {"id": "CTRL-003", "control": "watchdog and bounded command timeout", "gate": "required"},
        {"id": "CTRL-004", "control": "independent interlock for hazardous physical motion", "gate": "required_if_motion_hazard"},
        {"id": "CTRL-005", "control": "least-privilege actuator and device permissions", "gate": "required"},
        {"id": "CTRL-006", "control": "signed/authenticated software and firmware update path", "gate": "required"},
        {"id": "CTRL-007", "control": "SBOM and third-party component provenance", "gate": "required"},
        {"id": "CTRL-008", "control": "audit log for mission/design approval and runtime state", "gate": "required"},
        {"id": "CTRL-009", "control": "patent claim-level review before commercial release", "gate": "human_review"},
        {"id": "CTRL-010", "control": "jurisdiction applicability review before market release", "gate": "human_review"},
    ]
    if product_class == "collaborative-robot":
        controls.append({"id": "CTRL-COLLAB", "control": "collaborative-operation risk assessment and validated protective measures", "gate": "required"})
    if flags.get("ai"):
        controls.extend(
            [
                {"id": "CTRL-AI-001", "control": "human approval before physical mission execution", "gate": "required"},
                {"id": "CTRL-AI-002", "control": "model/version provenance and evaluation record", "gate": "required"},
                {"id": "CTRL-AI-003", "control": "fallback behavior when model output is unavailable or out of bounds", "gate": "required"},
            ]
        )
    if flags.get("wireless"):
        controls.append({"id": "CTRL-RF-001", "control": "radio module and antenna certification path review", "gate": "required"})
    return controls


def package_readme(package: dict) -> str:
    flags = [key for key, value in package["flags"].items() if value]
    return f"""# {package['name']} — GPT-DOUG-MAX schematic package

Generated: `{package['generated_at']}`

Product class: `{package['product_class']}`  
Jurisdictions: `{', '.join(package['jurisdictions'])}`  
Conditional sectors/features: `{', '.join(flags) if flags else 'none declared'}`

## Package contents

- `package.json` — machine-readable design contract and provenance.
- `architecture.mmd` — system architecture schematic.
- `electrical-block.mmd` — high-level power/safety/control block schematic.
- `software-flow.mmd` — software and approval flow.
- `compliance-matrix.json` — jurisdiction, agency, regulation, and standards preflight.
- `patent-boundary.json` — patent-informed concepts and independent-design boundaries.
- `design-controls.json` — safety, cybersecurity, provenance, and release controls.

## Patent/legal posture

The patent source is used as public prior-art evidence and an architecture signal. This package does **not** copy claim language, does not provide a freedom-to-operate opinion, and does not declare legal compliance. Claim-level analysis and commercial release require qualified human review.

## Release posture

`ENGINEERING_DRAFT_ONLY`. Unknown jurisdictions fail closed. Official sources must be rechecked before certification, conformity assessment, production, sale, export, or deployment.
"""


def make_package(args: argparse.Namespace) -> Path:
    registry = load_json(REGISTRY)
    patent = load_json(PATENT_SEED)
    if args.product_class not in PRODUCT_CLASSES:
        raise SystemExit(f"NO-GO: unsupported product class: {args.product_class}")
    check_scope(args.name, args.description or "")
    jurisdictions = normalize_jurisdictions(args.jurisdiction, registry)
    flags = {
        "wireless": bool(args.wireless),
        "ai": bool(args.ai),
        "medical": bool(args.medical),
        "uas": bool(args.uas),
        "road_vehicle": bool(args.road_vehicle),
        "consumer": bool(args.consumer),
        "critical_infrastructure": bool(args.critical_infrastructure),
        "export": bool(args.export),
    }
    matrix = compliance_matrix(registry, jurisdictions, args.product_class, flags)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(args.output).expanduser() if args.output else DEFAULT_OUTPUT_ROOT / f"{slug(args.name)}-{stamp}"
    if output.exists():
        if not args.force:
            raise SystemExit(f"NO-GO: output exists: {output} (use --force to replace)")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    package = {
        "schema": "xunia.gpt-doug-max.robotics-schematic-package.v1",
        "name": args.name,
        "description": args.description or "",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "release_posture": "ENGINEERING_DRAFT_ONLY",
        "product_class": args.product_class,
        "jurisdictions": jurisdictions,
        "flags": flags,
        "patent_evidence": [patent["patent_id"]],
        "provenance": {
            "patent_seed": str(PATENT_SEED.relative_to(ROOT)),
            "compliance_registry": str(REGISTRY.relative_to(ROOT)),
            "registry_as_of": registry.get("as_of"),
        },
        "execution_policy": {
            "generated_mission_auto_execution": False,
            "human_approval_required": True,
            "unknown_jurisdiction_fails_closed": True,
            "claim_copying": False,
            "freedom_to_operate_opinion": False,
        },
        "interfaces": {
            "sensors": args.sensor or ["position/health sensor"],
            "actuators": args.actuator or ["bounded actuator interface"],
            "communications": args.interface or ["local authenticated control bus"],
        },
    }

    patent_boundary = {
        "schema": "xunia.patent-boundary.v1",
        "patent_id": patent["patent_id"],
        "title": patent["title"],
        "publicly_described_functional_concepts": patent["publicly_described_functional_concepts"],
        "independent_design_policy": patent["independent_design_policy"],
        "design_divergence_defaults": patent["design_divergence_defaults"],
        "decision": "HUMAN_CLAIM_REVIEW_REQUIRED_BEFORE_COMMERCIAL_RELEASE",
    }

    write_json(output / "package.json", package)
    write_json(
        output / "compliance-matrix.json",
        {
            "schema": "xunia.robotics-compliance-matrix.v1",
            "registry_as_of": registry.get("as_of"),
            "jurisdictions": jurisdictions,
            "rows": matrix,
            "decision": "HUMAN_APPLICABILITY_REVIEW_REQUIRED",
            "legal_advice": False,
        },
    )
    write_json(output / "patent-boundary.json", patent_boundary)
    write_json(
        output / "design-controls.json",
        {
            "schema": "xunia.robotics-design-controls.v1",
            "product_class": args.product_class,
            "controls": design_controls(args.product_class, flags),
            "release_gate": "HUMAN_ENGINEERING_AND_LEGAL_REVIEW",
        },
    )
    (output / "architecture.mmd").write_text(architecture_mermaid(args.product_class, args.ai), encoding="utf-8")
    (output / "electrical-block.mmd").write_text(electrical_mermaid(args.product_class), encoding="utf-8")
    (output / "software-flow.mmd").write_text(software_mermaid(args.ai), encoding="utf-8")
    (output / "README.md").write_text(package_readme(package), encoding="utf-8")
    return output


def status() -> int:
    registry = load_json(REGISTRY)
    patent = load_json(PATENT_SEED)
    print("GPT-DOUG-MAX // PATENT ROBOTICS + COMPLIANCE LAB")
    print("=================================================")
    print("Registry ........", registry.get("schema"))
    print("Registry as-of ..", registry.get("as_of"))
    print("Jurisdictions ...", ", ".join(sorted(registry.get("jurisdictions", {}))))
    print("Patent seed .....", patent.get("patent_id"), "//", patent.get("title"))
    print("Claim copying ... DISABLED")
    print("FTO opinion ..... DISABLED")
    print("Unknown territory BLOCKED")
    print("Release ......... HUMAN ENGINEERING + LEGAL REVIEW")
    return 0


def show_patent() -> int:
    patent = load_json(PATENT_SEED)
    print(json.dumps(patent, indent=2, sort_keys=True))
    return 0


def show_compliance(args: argparse.Namespace) -> int:
    registry = load_json(REGISTRY)
    jurisdictions = normalize_jurisdictions(args.jurisdiction, registry)
    flags = {
        "wireless": bool(args.wireless),
        "ai": bool(args.ai),
        "medical": bool(args.medical),
        "uas": bool(args.uas),
        "road_vehicle": bool(args.road_vehicle),
        "consumer": bool(args.consumer),
        "critical_infrastructure": bool(args.critical_infrastructure),
        "export": bool(args.export),
    }
    rows = compliance_matrix(registry, jurisdictions, args.product_class, flags)
    print(json.dumps({"jurisdictions": jurisdictions, "flags": flags, "rows": rows}, indent=2))
    return 0


def add_profile_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--product-class", choices=sorted(PRODUCT_CLASSES), default="industrial-robot")
    parser.add_argument("--jurisdiction", action="append", default=[])
    parser.add_argument("--wireless", action="store_true")
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--medical", action="store_true")
    parser.add_argument("--uas", action="store_true")
    parser.add_argument("--road-vehicle", action="store_true", dest="road_vehicle")
    parser.add_argument("--consumer", action="store_true")
    parser.add_argument("--critical-infrastructure", action="store_true", dest="critical_infrastructure")
    parser.add_argument("--export", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(prog="doug-max robotics-lab")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")
    sub.add_parser("patent")

    compliance = sub.add_parser("compliance")
    add_profile_flags(compliance)

    schematic = sub.add_parser("schematic")
    schematic.add_argument("--name", required=True)
    schematic.add_argument("--description", default="")
    add_profile_flags(schematic)
    schematic.add_argument("--sensor", action="append", default=[])
    schematic.add_argument("--actuator", action="append", default=[])
    schematic.add_argument("--interface", action="append", default=[])
    schematic.add_argument("--output")
    schematic.add_argument("--force", action="store_true")

    args = parser.parse_args()
    command = args.command or "status"
    if command == "status":
        return status()
    if command == "patent":
        return show_patent()
    if command == "compliance":
        return show_compliance(args)
    if command == "schematic":
        output = make_package(args)
        print("GPT-DOUG-MAX ROBOTICS SCHEMATIC : GENERATED")
        print("OUTPUT  :", output)
        print("STATUS  : ENGINEERING_DRAFT_ONLY")
        print("PATENT  : HUMAN CLAIM REVIEW REQUIRED")
        print("LEGAL   : NOT A FREEDOM-TO-OPERATE OPINION")
        print("RELEASE : HUMAN ENGINEERING + LEGAL REVIEW REQUIRED")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
