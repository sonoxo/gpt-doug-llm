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


def test_influenza_patent_is_learned_as_high_level_restricted_scope() -> None:
    result = run("show", "US-20260263586-A1")
    assert result.returncode == 0, result.stdout + result.stderr
    seed = json.loads(result.stdout)
    assert seed["title"] == "Influenza B virus mutants and uses therefor"
    assert "influenza-b" in seed["scope_tags"]
    assert seed["safety_scope"]["classification"] == "RESTRICTED_BIOLOGICAL_PATHOGEN_ENGINEERING"
    assert seed["safety_scope"]["sequence_data_stored"] is False
    assert seed["safety_scope"]["wet_lab_protocols_stored"] is False
    assert seed["scope_usage_policy"]["engineering_pattern_generation"] is False
    assert seed["scope_usage_policy"]["sequence_retrieval_or_design"] is False
    assert seed["scope_usage_policy"]["virus_rescue_or_propagation_protocol_generation"] is False


def test_scope_doctor_accepts_restricted_biological_seed() -> None:
    result = run("doctor")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PATENT SCOPE DOCTOR: GREEN" in result.stdout
