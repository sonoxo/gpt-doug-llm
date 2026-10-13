"""Offline fabrication design planner and 3D preview CLI."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core import DesignError, export_package

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "fabrication_brain" / "utility_rover.json"

def main(argv=None):
    parser = argparse.ArgumentParser(prog="gpt-doug-fab", description="Offline mechanical/welding/3D printing/assembly review")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("demo", "plan"):
        p = sub.add_parser(command)
        if command == "plan": p.add_argument("design", type=Path)
        p.add_argument("--output", type=Path, default=Path("build/fabrication-demo" if command == "demo" else "build/fabrication-plan"))
        p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.command == "status":
        print(json.dumps({"system":"GPT-DOUG FABRICATION BRAIN","mode":"OFFLINE_ENGINEERING_DRAFT","domains":["welding","mechanical","vehicles","robotics","3d_printing","assembly"],"hardware_control":False,"safety_release":"HUMAN_ONLY"}, indent=2))
        return 0
    source = EXAMPLE if args.command == "demo" else args.design
    try:
        design = json.loads(source.read_text(encoding="utf-8"))
        report = export_package(design, args.output, force=args.force)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, DesignError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"ok":True,"output":str(args.output),"status":report["summary"]["release_posture"],"readiness":report["summary"]["manufacturing_readiness"],"blocker_count":len(report["blockers"]),"warning_count":len(report["warnings"]),"preview":str(args.output / "preview.html")},indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
