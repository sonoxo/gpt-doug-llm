from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "gpt_doug_max_patent_scope.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_scope_doctor_green() -> None:
    result = run("doctor")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PATENT SCOPE DOCTOR: GREEN" in result.stdout
    assert "Seeds ............ 2" in result.stdout


def test_scope_library_contains_both_patents() -> None:
    result = run("list", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads(result.stdout)
    ids = {row["patent_id"] for row in rows}
    assert "US-12697722-B2" in ids
    assert "US-20260201971-A9" in ids


def test_fluid_control_scope_matches_fluid_query() -> None:
    result = run("match", "pressure sensor supply exhaust valve pneumatic actuator", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["patent_id"] == "US-20260201971-A9"
    assert payload["results"][0]["score"] > 0


def test_robot_mission_scope_matches_planning_query() -> None:
    result = run("match", "robot mission metrics heterogeneous fleet task planning", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["patent_id"] == "US-12697722-B2"
    assert payload["results"][0]["score"] > 0


def test_fluid_seed_keeps_independent_design_gate() -> None:
    result = run("show", "US-20260201971-A9")
    assert result.returncode == 0, result.stdout + result.stderr
    seed = json.loads(result.stdout)
    policy = seed["independent_design_policy"]
    assert policy["copy_claim_language"] is False
    assert policy["assert_freedom_to_operate"] is False
    assert policy["claim_element_mapping_requires_human_review"] is True
