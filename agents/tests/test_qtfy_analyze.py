import json
from pathlib import Path

from agents.qtfy_analyze import analyze, build_analysis


def test_build_analysis_contains_core_sections():
    source = Path("intel/qtfy/JCSA-20260826-01.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    report = build_analysis(data)
    assert "Chronological campaign timeline" in report
    assert "Organization → tool → CVE → event relationship map" in report
    assert "MITRE ATT&CK mapping" in report
    assert "Evidence gaps requiring human review" in report
    assert "INVESTIGATE_AND_VET" in report
    assert "CVE-2026-1731" in report


def test_analyze_writes_report(tmp_path):
    source = Path("intel/qtfy/JCSA-20260826-01.json")
    output = tmp_path / "qtfy-analysis.md"
    result = analyze(source, output)
    assert result == output
    text = output.read_text(encoding="utf-8")
    assert "JCSA-20260826-01" in text
    assert "No external systems were accessed" in text
