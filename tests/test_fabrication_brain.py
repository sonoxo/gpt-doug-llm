"""Fabrication Brain integration smoke and negative tests."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from fabrication_brain.core import DesignError, export_package, plan_design
from fabrication_brain.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "fabrication_brain" / "utility_rover.json"

def sample():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))

def test_example_package(tmp_path):
    report = export_package(sample(), tmp_path / "package")
    assert report["summary"]["part_count"] == 6
    assert report["summary"]["release_posture"] == "ENGINEERING_DRAFT_ONLY"
    assert report["execution_policy"]["remote_actuation"] is False
    assert report["execution_policy"]["gcode_generated"] is False
    for name in ("preview.html","assembly-preview.scad","assembly.mmd","bom.csv","review.json","assembly-plan.json"):
        assert (tmp_path / "package" / name).is_file()

def test_cli_demo(tmp_path):
    assert main(["demo","--output",str(tmp_path / "rover")]) == 0
    assert (tmp_path / "rover" / "preview.html").is_file()

def test_unknown_printer_material_is_blocked():
    data=sample()
    data["workspace"]["print_materials"]=[]
    report=plan_design(data)
    assert any(item["code"]=="PRINT_MATERIAL_NOT_QUALIFIED" for item in report["blockers"])

def test_cycle_fails_closed():
    data=sample()
    data["parts"][0]["depends_on"]=["crossmember"]
    with pytest.raises(DesignError,match="cyclic"):
        plan_design(data)

def test_unapproved_design_scope_fails_closed():
    data=sample()
    data["intent"]="weapon targeting system"
    with pytest.raises(DesignError):
        plan_design(data)

def test_status(capsys):
    assert main(["status"]) == 0
    assert json.loads(capsys.readouterr().out)["hardware_control"] is False
