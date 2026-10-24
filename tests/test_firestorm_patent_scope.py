"""Regression checks for provenance-gated wildfire patent learning."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "gpt_doug_max_patent_scope.py"
PATENT_ID = "US-20260273318-A1"

def invoke(*args: str) -> dict:
    result = subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)

def test_firestorm_patent_source_and_metadata():
    seed = invoke("show", PATENT_ID)
    assert seed["schema"] == "xunia.patent-robotics.seed.v1"
    assert seed["publication_date"] == "2026-09-17"
    assert seed["verification"]["official_pdf_retrieved_in_current_environment"] is False
    assert seed["source_provenance"][0]["source_text_sha256"] == (
        "054ab6305cfdfaed6e11811c0aae898aae1a578f8df5917914732b1fac4e0a93"
    )

def test_firestorm_patent_retrievable_and_safe():
    results = invoke("match", "firestorm wildfire shielded soffit vent attic ember intrusion", "--json")
    assert results["results"][0]["patent_id"] == PATENT_ID
    seed = invoke("show", PATENT_ID)
    assert seed["building_memory"]["default_build_profile"] == "CIVILIAN_WILDFIRE_BUILDING_ENVELOPE_RESEARCH"
    assert seed["safety_policy"]["real_world_actuation_enabled"] is False
    assert seed["safety_policy"]["automatic_vent_closure_enabled"] is False
    assert seed["safety_policy"]["physical_test_evidence_required_before_performance_claims"] is True
    assert seed["independent_design_policy"]["copy_claim_language"] is False
    assert seed["independent_design_policy"]["assert_freedom_to_operate"] is False
    assert seed["independent_design_policy"]["commercial_release_requires_patent_counsel_review"] is True
