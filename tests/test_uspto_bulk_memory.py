from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.uspto_bulk_memory import initialize, import_file, ppubs_permalink, write_manifest


def test_bulk_import_generates_stable_permalinks_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "patents.csv"
    source.write_text(
        "patent_number,title,abstract,assignee,patent_date\n"
        "12744799,Correlating distinct events,Security event correlation,FORTINET,2026-09-22\n"
        "12744803,Multi-layer anomaly detector,Layered anomaly detection,MICROSOFT,2026-09-22\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    out.mkdir()
    db = out / "uspto-bulk-memory.sqlite3"
    con = initialize(db)
    report = import_file(con, source)
    manifest = write_manifest(con, out, None)
    con.close()

    assert report["imported_rows"] == 2
    assert manifest["patent_records_indexed"] == 2
    assert manifest["all_uspto_patents_claimed"] is False

    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT document_number,ppubs_permalink FROM patents ORDER BY document_number"
    ).fetchall()
    con.close()
    assert rows[0][1] == ppubs_permalink(rows[0][0])
    assert "ppubs.uspto.gov/pubwebapp/external.html" in rows[1][1]


def test_expected_manifest_can_prove_only_supplied_artifact_set(tmp_path: Path) -> None:
    source = tmp_path / "patents.jsonl"
    source.write_text(
        json.dumps({"patent_number": "12744793", "title": "Cybersecurity components and LLMs"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    out.mkdir()
    db = out / "uspto-bulk-memory.sqlite3"
    con = initialize(db)
    report = import_file(con, source)

    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps({"artifacts": [{"filename": source.name, "sha256": report["sha256"]}]}),
        encoding="utf-8",
    )
    manifest = write_manifest(con, out, expected)
    con.close()

    assert manifest["complete_for_expected_manifest"] is True
    assert manifest["all_uspto_patents_claimed"] is False
