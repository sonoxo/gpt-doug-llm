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
    assert "Unknown scope ...... FAIL-CLOSED" in result.stdout


def test_scope_library_contains_validated_patents() -> None:
    result = run("list", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads(result.stdout)
    ids = {row["patent_id"] for row in rows}
    assert {
        "US-12697722-B2",
        "US-20260201971-A9",
        "US-20250355943-A1",
    } <= ids
    assert "US-20260271508-A1" not in ids


def test_new_patent_is_registered_as_pending_not_invented_scope() -> None:
    result = run("pending", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads(result.stdout)
    row = next(x for x in rows if x["patent_id"] == "US-20260271508-A1")
    assert row["status"] == "PENDING_SCOPE_EXTRACTION"
    assert row["official_document_text_retrieved"] is False

    shown = run("show", "US-20260271508-A1")
    assert shown.returncode == 0, shown.stdout + shown.stderr
    intake = json.loads(shown.stdout)
    assert intake["scope_policy"]["infer_scope_without_document"] is False
    assert intake["source"]["request_token_persisted"] is False


def test_pending_patent_is_excluded_from_scope_ranking() -> None:
    result = run("match", "pressure sensor supply exhaust valve pneumatic actuator", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert "US-20260271508-A1" in payload["pending_patents_excluded_from_scope_ranking"]
    assert payload["results"][0]["patent_id"] == "US-20260201971-A9"


def test_fluid_control_scope_matches_fluid_query() -> None:
    result = run("match", "pressure sensor supply exhaust valve pneumatic actuator", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["patent_id"] == "US-20260201971-A9"


def test_robot_mission_scope_matches_planning_query() -> None:
    result = run("match", "robot mission metrics heterogeneous fleet task planning", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["patent_id"] == "US-12697722-B2"


def test_system_event_detection_scope_matches_defensive_security_query() -> None:
    result = run(
        "match",
        "cybersecurity event object graph entity descriptor SIEM incident triage defensive response",
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["patent_id"] == "US-20250355943-A1"


def test_system_event_detection_seed_keeps_defensive_response_gates() -> None:
    result = run("show", "US-20250355943-A1")
    assert result.returncode == 0, result.stdout + result.stderr
    seed = json.loads(result.stdout)
    policy = seed["defensive_security_policy"]
    assert policy["authorized_security_data_only"] is True
    assert policy["human_review_for_consequential_actions"] is True
    assert policy["automatic_device_isolation"] is False
    assert policy["automatic_permission_revocation"] is False
    assert policy["automatic_file_deletion"] is False
    assert policy["offensive_exploitation"] is False


def test_fluid_seed_keeps_independent_design_gate() -> None:
    result = run("show", "US-20260201971-A9")
    assert result.returncode == 0, result.stdout + result.stderr
    seed = json.loads(result.stdout)
    policy = seed["independent_design_policy"]
    assert policy["copy_claim_language"] is False
    assert policy["assert_freedom_to_operate"] is False
    assert policy["claim_element_mapping_requires_human_review"] is True
