from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "gpt_doug_max_robotics_lab.py"
PATENT_BRIDGE = ROOT / "scripts" / "gpt_doug_max_patent_bridge.py"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def test_status_and_patent_seed_are_wired() -> None:
    status = run("status")
    assert "PATENT ROBOTICS + COMPLIANCE LAB" in status.stdout
    assert "US-12697722-B2" in status.stdout

    patent = run("patent")
    data = json.loads(patent.stdout)
    assert data["patent_id"] == "US-12697722-B2"
    assert data["independent_design_policy"]["copy_claim_language"] is False
    assert data["independent_design_policy"]["assert_freedom_to_operate"] is False


def test_generates_complete_governed_schematic_package(tmp_path: Path) -> None:
    output = tmp_path / "inspection-rover"
    result = run(
        "schematic",
        "--name",
        "Plant Inspection Rover",
        "--description",
        "Operator-approved indoor inspection robot",
        "--product-class",
        "mobile-robot",
        "--jurisdiction",
        "US",
        "--jurisdiction",
        "EU",
        "--ai",
        "--wireless",
        "--sensor",
        "camera",
        "--sensor",
        "lidar",
        "--actuator",
        "low-voltage traction motor",
        "--output",
        str(output),
    )
    assert "GENERATED" in result.stdout

    expected = {
        "package.json",
        "architecture.mmd",
        "electrical-block.mmd",
        "software-flow.mmd",
        "compliance-matrix.json",
        "patent-boundary.json",
        "design-controls.json",
        "README.md",
    }
    assert expected == {p.name for p in output.iterdir()}

    package = json.loads((output / "package.json").read_text())
    assert package["jurisdictions"] == ["US", "EU"]
    assert package["execution_policy"]["generated_mission_auto_execution"] is False
    assert package["execution_policy"]["human_approval_required"] is True
    assert package["execution_policy"]["freedom_to_operate_opinion"] is False

    matrix = json.loads((output / "compliance-matrix.json").read_text())
    ids = {row["requirement"] for row in matrix["rows"]}
    assert "OSHA-29-CFR-1910.212" in ids
    assert "EU-2023/1230" in ids
    assert "EU-2024/1689" in ids
    assert "FCC-47-CFR-PART-15" in ids

    boundary = json.loads((output / "patent-boundary.json").read_text())
    assert boundary["patent_id"] == "US-12697722-B2"
    assert boundary["decision"] == "HUMAN_CLAIM_REVIEW_REQUIRED_BEFORE_COMMERCIAL_RELEASE"


def test_unknown_jurisdiction_fails_closed(tmp_path: Path) -> None:
    result = run(
        "schematic",
        "--name",
        "Bench Robot",
        "--jurisdiction",
        "ZZ",
        "--output",
        str(tmp_path / "bad"),
        check=False,
    )
    assert result.returncode != 0
    assert "NO-GO" in (result.stdout + result.stderr)


def test_weapon_or_targeting_scope_is_rejected(tmp_path: Path) -> None:
    result = run(
        "schematic",
        "--name",
        "Autonomous targeting robot",
        "--jurisdiction",
        "US",
        "--output",
        str(tmp_path / "blocked"),
        check=False,
    )
    assert result.returncode != 0
    assert "blocked capability" in (result.stdout + result.stderr)


def test_patent_wiring_doctor_includes_robotics_lab() -> None:
    proc = subprocess.run(
        [sys.executable, str(PATENT_BRIDGE), "doctor"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Robotics lab .... wired" in proc.stdout
    assert "Compliance ...... fail-closed" in proc.stdout
