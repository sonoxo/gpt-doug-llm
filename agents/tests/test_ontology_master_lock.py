import json
from pathlib import Path

import pytest

from agents.ontology_master_lock import (
    DEFAULT_ANALYSIS,
    DEFAULT_LOCK,
    DEFAULT_ONTOLOGY,
    DEFAULT_SOURCE,
    MasterLockError,
    run_master_lock,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_source(root: Path) -> Path:
    target = root / DEFAULT_SOURCE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((REPO_ROOT / DEFAULT_SOURCE).read_bytes())
    return target


def test_master_lock_publishes_only_after_all_subagents_pass(tmp_path):
    _copy_source(tmp_path)

    report = run_master_lock(tmp_path)

    assert report["locked"] is True
    assert report["publicationState"] == "LOCKED_AND_PUBLISHABLE"
    assert [stage["subagent"] for stage in report["subagents"]] == [
        "source-agent",
        "ontology-builder-agent",
        "ontology-validator-agent",
        "analysis-agent",
        "master-lock-agent",
    ]
    assert all(stage["status"] == "PASS" for stage in report["subagents"])

    analysis_path = tmp_path / DEFAULT_ANALYSIS
    ontology_path = tmp_path / DEFAULT_ONTOLOGY
    lock_path = tmp_path / DEFAULT_LOCK
    assert analysis_path.is_file()
    assert ontology_path.is_file()
    assert lock_path.is_file()

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    assert lock["lockId"] == report["lockId"]
    assert lock["guardrails"]["allSubagentsMustPass"] is True
    assert ontology["guardrails"]["masterLockRequiredForPublish"] is True
    assert "Source p." in analysis_path.read_text(encoding="utf-8")


def test_master_lock_refuses_unsafe_source_policy_without_publishing(tmp_path):
    source_path = _copy_source(tmp_path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    data["iocPolicy"]["automaticBlocking"] = True
    source_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(MasterLockError, match="automatic IOC blocking"):
        run_master_lock(tmp_path)

    assert not (tmp_path / DEFAULT_ANALYSIS).exists()
    assert not (tmp_path / DEFAULT_ONTOLOGY).exists()
    assert not (tmp_path / DEFAULT_LOCK).exists()


def test_master_lock_refuses_source_plan_drift(tmp_path):
    source_path = _copy_source(tmp_path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    data["tools"][0]["id"] = "unexpected-tool-id"
    source_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(MasterLockError, match="tools source/plan id drift"):
        run_master_lock(tmp_path)

    assert not (tmp_path / DEFAULT_LOCK).exists()
