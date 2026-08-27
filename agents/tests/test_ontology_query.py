from pathlib import Path

import pytest

from agents.ontology_master_lock import run_master_lock
from agents.ontology_query import (
    OntologyQueryError,
    load_locked_package,
    ontology_brief,
    ontology_gaps,
    ontology_query,
    ontology_status,
    ontology_timeline,
)

ROOT = Path(__file__).resolve().parents[2]


def _locked_workspace(tmp_path: Path) -> Path:
    source = ROOT / "intel/qtfy/JCSA-20260826-01.json"
    target = tmp_path / "intel/qtfy/JCSA-20260826-01.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    run_master_lock(tmp_path)
    return tmp_path


def test_query_engine_reads_only_verified_master_lock(tmp_path):
    root = _locked_workspace(tmp_path)
    package = load_locked_package(root)

    status = ontology_status(package)
    assert "MASTER LOCK VERIFIED" in status
    assert "Objects: 61" in status
    assert "Links: 82" in status

    timeline = ontology_timeline(package)
    assert "2018-05" in timeline
    assert "2026-06" in timeline
    assert "Source p." in timeline

    query = ontology_query(package, "QScan CVE-2024-24919")
    assert "qscan" in query.lower()
    assert "CVE-2024-24919" in query
    assert "EventReferencesVulnerability" in query or "AdvisoryMentionsVulnerability" in query

    brief = ontology_brief(package)
    assert "MASTER-LOCKED DEFENSIVE INTELLIGENCE BRIEF" in brief
    assert "authorizedOnly=True" in brief

    gaps = ontology_gaps(package)
    assert "linkage gaps" in gaps
    assert "absence of a link does not prove absence" in gaps


def test_query_engine_rejects_tampered_locked_output(tmp_path):
    root = _locked_workspace(tmp_path)
    ontology = root / "intel/qtfy/qtfy-ontology-runtime.json"
    ontology.write_text(ontology.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(OntologyQueryError, match="hash mismatch"):
        load_locked_package(root)
