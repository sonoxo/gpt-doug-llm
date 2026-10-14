"""Deterministic, offline fabrication planning with fail-closed physical release policy.

This module does not perform structural FEA, weld sizing, slicing, robot inverse
kinematics or collision checking. Outputs are engineering review artifacts only.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMA = "xunia.fabrication.design.v1"
CATEGORIES = {"workshop_fixture", "vehicle_subassembly", "mobile_robot", "robotic_cell", "mechatronics"}
PROCESSES = {"fdm_print", "stock", "machined", "purchased"}
JOINTS = {"weld", "bolt", "press_fit", "adhesive"}
METALS = {"mild_steel", "carbon_steel", "stainless_steel", "aluminum"}
WELD_PAIRS = {frozenset(("mild_steel", "carbon_steel")), frozenset(("mild_steel",)),
              frozenset(("carbon_steel",)), frozenset(("stainless_steel",)),
              frozenset(("aluminum",))}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
DENIED_TERMS = re.compile(r"\b(?:weapon|munition|missile|explosive|fire[ -]?control|autonomous[ -]?engagement|targeting system)\b", re.I)


class DesignError(ValueError):
    """Invalid or unsafe-to-model input design."""


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignError(f"{label} must be nonempty text")
    return value.strip()


def _id(value: Any, label: str) -> str:
    value = _string(value, label)
    if not ID_PATTERN.fullmatch(value):
        raise DesignError(f"{label} must match {ID_PATTERN.pattern}")
    return value


def _number(value: Any, label: str, *, strictly_positive: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DesignError(f"{label} must be a finite number")
    if (value <= 0 if strictly_positive else value < 0):
        raise DesignError(f"{label} must be {'positive' if strictly_positive else 'nonnegative'}")
    return float(value)


def _vector(value: Any, label: str, *, positive: bool) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise DesignError(f"{label} must be a three-element array")
    result = []
    for index, item in enumerate(value):
        if positive:
            result.append(_number(item, f"{label}[{index}]"))
        else:
            if isinstance(item, bool) or not isinstance(item, (float, int)) or not math.isfinite(item):
                raise DesignError(f"{label}[{index}] must be a finite number")
            result.append(float(item))
    return result


def _unique_ids(items: list[dict], label: str) -> None:
    seen: set[str] = set()
    for item in items:
        key = item["id"]
        if key in seen:
            raise DesignError(f"duplicate {label} id: {key}")
        seen.add(key)


def validate(design: Any) -> dict:
    if not isinstance(design, dict):
        raise DesignError("design must be a JSON object")
    if design.get("schema") != SCHEMA:
        raise DesignError(f"schema must be {SCHEMA}")
    title = _string(design.get("name"), "name")
    intent = _string(design.get("intent"), "intent")
    if DENIED_TERMS.search(title + " " + intent):
        raise DesignError("civilian/industrial designs only: weapon or targeting scope denied")
    category = design.get("category")
    if category not in CATEGORIES:
        raise DesignError(f"category must be one of {sorted(CATEGORIES)}")
    if design.get("units") != "mm":
        raise DesignError("units must be explicit: mm")
    parts = design.get("parts")
    if not isinstance(parts, list) or not parts or len(parts) > 200:
        raise DesignError("parts must contain 1 to 200 entries")
    normalized_parts = []
    for i, part in enumerate(parts):
        if not isinstance(part, dict):
            raise DesignError(f"parts[{i}] must be an object")
        process = part.get("process")
        if process not in PROCESSES:
            raise DesignError(f"parts[{i}].process invalid: {process}")
        material = _string(part.get("material"), f"parts[{i}].material").lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,48}", material):
            raise DesignError("material must be a simple material ID")
        quantity = part.get("quantity", 1)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000:
            raise DesignError(f"parts[{i}].quantity must be an integer in 1..1000")
        mass = part.get("mass_kg")
        if mass is not None:
            mass = _number(mass, f"parts[{i}].mass_kg", strictly_positive=False)
        dependencies = part.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(d, str) for d in dependencies):
            raise DesignError(f"parts[{i}].depends_on must be a list of IDs")
        if len(set(dependencies)) != len(dependencies):
            raise DesignError(f"parts[{i}].depends_on repeats a dependency")
        normalized_parts.append({
            "id": _id(part.get("id"), f"parts[{i}].id"),
            "name": _string(part.get("name"), f"parts[{i}].name"),
            "material": material,
            "process": process,
            "size_mm": _vector(part.get("size_mm"), f"parts[{i}].size_mm", positive=True),
            "center_mm": _vector(part.get("center_mm"), f"parts[{i}].center_mm", positive=False),
            "quantity": quantity,
            "mass_kg": mass,
            "load_bearing": part.get("load_bearing", False),
            "depends_on": dependencies,
        })
        if not isinstance(normalized_parts[-1]["load_bearing"], bool):
            raise DesignError(f"parts[{i}].load_bearing must be boolean")
    _unique_ids(normalized_parts, "part")
    ids = {p["id"] for p in normalized_parts}
    for p in normalized_parts:
        for dep in p["depends_on"]:
            if dep not in ids or dep == p["id"]:
                raise DesignError(f"invalid dependency: {p['id']} -> {dep}")

    raw_joints = design.get("joints", [])
    if not isinstance(raw_joints, list) or len(raw_joints) > 400:
        raise DesignError("joints must be a list of at most 400 entries")
    joints = []
    for i, joint in enumerate(raw_joints):
        if not isinstance(joint, dict):
            raise DesignError(f"joints[{i}] must be an object")
        kind = joint.get("kind")
        if kind not in JOINTS:
            raise DesignError(f"joints[{i}].kind invalid: {kind}")
        connects = joint.get("connects")
        if not isinstance(connects, list) or len(connects) != 2 or any(not isinstance(v, str) for v in connects):
            raise DesignError(f"joints[{i}].connects must contain two part IDs")
        if connects[0] == connects[1] or any(v not in ids for v in connects):
            raise DesignError(f"joints[{i}] references missing/identical parts")
        joints.append({"id": _id(joint.get("id"), f"joints[{i}].id"), "kind": kind, "connects": connects})
    _unique_ids(joints, "joint")

    workspace = design.get("workspace", {})
    if not isinstance(workspace, dict):
        raise DesignError("workspace must be an object")
    printer_bed = workspace.get("printer_bed_mm")
    if printer_bed is not None:
        printer_bed = _vector(printer_bed, "workspace.printer_bed_mm", positive=True)
    reach = workspace.get("robot_reach_mm")
    if reach is not None:
        reach = _number(reach, "workspace.robot_reach_mm")
    supported = workspace.get("print_materials", [])
    if not isinstance(supported, list) or any(not isinstance(s, str) for s in supported):
        raise DesignError("workspace.print_materials must be a list of strings")
    print_materials = sorted(set(s.lower().strip() for s in supported if s.strip()))
    return {
        "schema": SCHEMA,
        "name": title,
        "intent": intent,
        "category": category,
        "units": "mm",
        "parts": normalized_parts,
        "joints": joints,
        "workspace": {"printer_bed_mm": printer_bed, "robot_reach_mm": reach, "print_materials": print_materials},
    }


def _assembly_order(parts: list[dict]) -> list[str]:
    dependencies = {p["id"]: set(p["depends_on"]) for p in parts}
    ordered: list[str] = []
    while dependencies:
        available = sorted(k for k, deps in dependencies.items() if not deps)
        if not available:
            raise DesignError("cyclic assembly dependency")
        ordered.extend(available)
        for key in available:
            del dependencies[key]
        for deps in dependencies.values():
            deps.difference_update(available)
    return ordered


def _envelope(parts: list[dict]) -> dict:
    mins = [min(p["center_mm"][i] - p["size_mm"][i] / 2 for p in parts) for i in range(3)]
    maxes = [max(p["center_mm"][i] + p["size_mm"][i] / 2 for p in parts) for i in range(3)]
    return {"min_mm": mins, "max_mm": maxes, "dimensions_mm": [maxes[i] - mins[i] for i in range(3)]}


def plan_design(source: Any) -> dict:
    """Return a reproducible, review-only manufacturing package (no device commands)."""
    design = validate(source)
    order = _assembly_order(design["parts"])
    lookup = {p["id"]: p for p in design["parts"]}
    workspace = design["workspace"]
    blockers: list[dict] = []
    warnings: list[dict] = []
    checks: list[dict] = []

    def issue(target: list[dict], code: str, subject: str, detail: str) -> None:
        target.append({"code": code, "subject": subject, "detail": detail})

    for p in design["parts"]:
        if p["mass_kg"] is None:
            issue(warnings, "MASS_UNSPECIFIED", p["id"], "Total mass cannot be fully assessed")
        if p["process"] == "fdm_print":
            bed = workspace["printer_bed_mm"]
            if bed is None:
                issue(blockers, "PRINTER_UNSPECIFIED", p["id"], "Printer build volume must be supplied")
                fits = False
            else:
                fits = any(all(dim <= max_dim for dim, max_dim in zip(permutation, bed))
                           for permutation in set(itertools.permutations(p["size_mm"])))
                if not fits:
                    issue(blockers, "PRINT_ENVELOPE_EXCEEDED", p["id"], "Bounding box does not fit in build volume in any axis permutation")
            if p["material"] not in workspace["print_materials"]:
                issue(blockers, "PRINT_MATERIAL_NOT_QUALIFIED", p["id"], "Material not listed in declared printer capability")
            if p["load_bearing"]:
                issue(warnings, "PRINT_STRENGTH_UNVERIFIED", p["id"], "Printed structural part requires load, anisotropy, temperature and fatigue validation")
            checks.append({"part_id": p["id"], "process": "fdm_print", "bbox_fits_bed": fits,
                           "slicer_output_generated": False, "orientation_or_supports_verified": False,
                           "material": p["material"]})
        else:
            checks.append({"part_id": p["id"], "process": p["process"], "geometry_verified": False})
    for joint in design["joints"]:
        a, b = (lookup[k] for k in joint["connects"])
        if joint["kind"] == "weld":
            pair = frozenset((a["material"], b["material"]))
            if pair not in WELD_PAIRS:
                issue(blockers, "WELD_MATERIAL_REVIEW", joint["id"], "Unsupported or dissimilar material pairing; qualified procedure required")
            if a["process"] == "fdm_print" or b["process"] == "fdm_print":
                issue(blockers, "WELD_PLASTIC_PART", joint["id"], "FDM plastic parts must not use the metal welding workflow")
            issue(warnings, "WPS_REQUIRED", joint["id"], "Certified welding procedure, fit-up, ventilation/fire controls and inspection required; no machine parameters generated")
        elif joint["kind"] == "bolt":
            issue(warnings, "FASTENER_VERIFICATION", joint["id"], "Engineer must select grade, joint design and approved torque")
        elif joint["kind"] == "press_fit":
            issue(warnings, "TOLERANCE_ANALYSIS", joint["id"], "Interference, tolerance and installation method require verification")
        elif joint["kind"] == "adhesive":
            issue(warnings, "BOND_QUALIFICATION", joint["id"], "Surface prep, compatibility and curing must be qualified")

        reach = workspace["robot_reach_mm"]
        if reach is not None:
            midpoint = [(a["center_mm"][i] + b["center_mm"][i]) / 2 for i in range(3)]
            distance = math.sqrt(sum(val * val for val in midpoint))
            if distance > reach:
                issue(blockers, "COARSE_ROBOT_REACH_EXCEEDED", joint["id"], "Joint midpoint beyond declared reach; frame assumes robot at [0,0,0]")
            else:
                issue(warnings, "ROBOT_IK_UNVERIFIED", joint["id"], "Coarse reach only: inverse kinematics, fixtures, collision, limits and workspace must be simulated")

    if design["category"] == "vehicle_subassembly":
        issue(warnings, "VEHICLE_VALIDATION_REQUIRED", design["name"], "Roadworthiness, structural fatigue, load paths, braking/steering interfaces and applicable approvals not evaluated")
    if design["category"] in {"mobile_robot", "robotic_cell"}:
        issue(warnings, "ROBOT_SAFETY_REVIEW", design["name"], "Machine guarding, safety-rated control, risk assessment and emergency stops require independent validation")

    tasks = []
    for part_id in order:
        p = lookup[part_id]
        tasks.append({"id": f"prepare-{part_id}", "type": "part_preparation", "part_ids": [part_id],
                      "depends_on": [f"prepare-{dep}" for dep in p["depends_on"]],
                      "instruction": f"Review fabrication/procurement and dimensional inspection for {p['name']}",
                      "machine_commands": []})
    for joint in design["joints"]:
        tasks.append({"id": f"review-{joint['id']}", "type": "joining_review", "joint_kind": joint["kind"],
                      "part_ids": joint["connects"],
                      "depends_on": [f"prepare-{part_id}" for part_id in joint["connects"]],
                      "instruction": "Qualified engineer / operator to approve joining procedure and inspection before manual execution",
                      "machine_commands": []})
    tasks.append({"id": "final-inspection", "type": "quality_release_review", "part_ids": [],
                  "depends_on": [t["id"] for t in tasks if t["type"] == "joining_review"] or
                                [t["id"] for t in tasks if t["type"] == "part_preparation"],
                  "instruction": "Dimensional, safety and function reviews; no automatic release", "machine_commands": []})

    canonical = json.dumps(design, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    known_mass = sum(p["mass_kg"] * p["quantity"] for p in design["parts"] if p["mass_kg"] is not None)
    mass_complete = all(p["mass_kg"] is not None for p in design["parts"])
    bom = [{key: p[key] for key in ("id", "name", "process", "material", "quantity", "mass_kg", "load_bearing")}
           for p in design["parts"]]
    return {
        "schema": "xunia.fabrication.review-package.v1",
        "design_sha256": digest,
        "design": design,
        "summary": {"release_posture": "ENGINEERING_DRAFT_ONLY", "manufacturing_readiness": "HOLD" if blockers else "REVIEW_REQUIRED",
                    "part_count": len(bom), "joint_count": len(design["joints"]), "envelope": _envelope(design["parts"]),
                    "total_input_mass_kg": round(known_mass, 6) if mass_complete else None,
                    "mass_data_complete": mass_complete},
        "bom": bom,
        "manufacturing_checks": checks,
        "assembly_plan": tasks,
        "blockers": blockers,
        "warnings": warnings,
        "approval_gates": ["mechanical_design_review", "structural_and_fatigue_analysis",
                           "welding_procedure_and_inspection", "additive_process_qualification",
                           "robot_cell_safety_and_collision_simulation", "machine_interlock_validation",
                           "applicable_vehicle_or_market_compliance", "operator_final_authorization"],
        "execution_policy": {"draft_only": True, "remote_actuation": False, "robot_program_generated": False,
                             "weld_settings_generated": False, "gcode_generated": False, "human_review_required": True,
                             "safety_plc_bypass": False},
        "limitations": ["Bounding-box geometry only, not manufacturable CAD or validated dimensional tolerances",
                        "Robot reach is a coarse geometric filter only, not collision or kinematic simulation",
                        "No welding parameters, actuator commands, certified weld strength, structural FEA or slicer toolpaths"],
    }


def _csv_bom(path: Path, bom: list[dict]) -> None:
    columns = ["id", "name", "process", "material", "quantity", "mass_kg", "load_bearing"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(bom)


def export_package(source: dict, output: Path, *, force: bool = False) -> dict:
    from .visual import html_view, mermaid_chart, scad_preview

    report = plan_design(source)
    output = Path(output).expanduser()
    if output.exists() and any(output.iterdir()) and not force:
        raise DesignError(f"output directory is not empty: {output} (use --force to overwrite generated files)")
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "design.normalized.json": json.dumps(report["design"], indent=2) + "\n",
        "review.json": json.dumps({k: v for k, v in report.items() if k != "design"}, indent=2) + "\n",
        "assembly-plan.json": json.dumps(report["assembly_plan"], indent=2) + "\n",
        "assembly.mmd": mermaid_chart(report),
        "assembly-preview.scad": scad_preview(report),
        "preview.html": html_view(report),
        "README.md": "# GPT-Doug Fabrication Brain review package\n\nOpen preview.html locally for an interactive bounding-box assembly view. Open assembly-preview.scad in OpenSCAD for a parametric proxy view. Neither is manufacturing-ready CAD. Review review.json, assembly-plan.json, and bom.csv before any physical work. Machine activation and production release are never automated.\n",
    }
    for filename, contents in files.items():
        (output / filename).write_text(contents, encoding="utf-8")
    _csv_bom(output / "bom.csv", report["bom"])
    return report
