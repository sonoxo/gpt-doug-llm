#!/usr/bin/env python3
"""Offline USPTO/PatentsView bulk-data memory importer for GPT-DOUG.

This script intentionally does not scrape millions of Patent Public Search pages.
It ingests official bulk exports that the operator has already downloaded from
USPTO Open Data / PatentsView, generates stable Patent Public Search permalinks,
hashes the input files, and builds a local SQLite/FTS evidence index.

Supported input shapes:
- CSV / TSV with a patent/document number column
- JSONL with one object per line

The importer never claims "all USPTO patents are in memory" unless the operator
supplies an expected manifest and every expected artifact is present, hashed, and
successfully imported.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DOC_RE = re.compile(r"(?:US[-\s]?)?(\d{7,11})(?:[-\s]?([A-Z]\d))?", re.I)
CANDIDATE_ID_COLUMNS = (
    "document_number",
    "patent_number",
    "patent_id",
    "publication_number",
    "publication_id",
    "id",
)
CANDIDATE_TITLE_COLUMNS = ("title", "patent_title", "invention_title")
CANDIDATE_ABSTRACT_COLUMNS = ("abstract", "patent_abstract")
CANDIDATE_ASSIGNEE_COLUMNS = ("assignee", "assignee_name", "organization")
CANDIDATE_DATE_COLUMNS = ("date", "patent_date", "publication_date", "grant_date")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_document_number(value: object) -> str | None:
    text = str(value or "").strip()
    match = DOC_RE.search(text)
    if not match:
        return None
    number = match.group(1)
    kind = (match.group(2) or "").upper()
    return f"US-{number}-{kind}" if kind else f"US-{number}"


def numeric_patent_number(document_number: str) -> str:
    match = DOC_RE.search(document_number)
    if not match:
        raise ValueError(f"invalid document number: {document_number}")
    return match.group(1)


def ppubs_permalink(document_number: str) -> str:
    number = numeric_patent_number(document_number)
    return (
        "https://ppubs.uspto.gov/pubwebapp/external.html"
        f"?q=({number}).pn.&db=USPAT&type=ids"
    )


def pick(row: dict[str, Any], keys: Iterable[str]) -> str:
    lower = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        value = lower.get(key.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def iter_csv(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        sample = handle.read(65536)
        handle.seek(0)
        delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            pass
        yield from csv.DictReader(handle, delimiter=delimiter)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                yield value


def iter_rows(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        yield from iter_jsonl(path)
        return
    if suffix in {".csv", ".tsv", ".tab"}:
        yield from iter_csv(path)
        return
    raise ValueError(f"unsupported bulk input type: {path}")


def initialize(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        """CREATE TABLE IF NOT EXISTS patents(
            document_number TEXT PRIMARY KEY,
            patent_number TEXT NOT NULL,
            title TEXT,
            abstract TEXT,
            assignee TEXT,
            published TEXT,
            ppubs_permalink TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            imported_at TEXT NOT NULL
        )"""
    )
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS patents_fts USING fts5(document_number,title,abstract,assignee)"
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS source_artifacts(
            source_file TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            bytes INTEGER NOT NULL,
            imported_rows INTEGER NOT NULL,
            skipped_rows INTEGER NOT NULL,
            imported_at TEXT NOT NULL
        )"""
    )
    return con


def import_file(con: sqlite3.Connection, path: Path) -> dict[str, Any]:
    path = path.resolve()
    source_hash = sha256(path)
    imported = 0
    skipped = 0
    for row in iter_rows(path):
        raw_id = pick(row, CANDIDATE_ID_COLUMNS)
        document_number = normalize_document_number(raw_id)
        if not document_number:
            skipped += 1
            continue
        title = pick(row, CANDIDATE_TITLE_COLUMNS)
        abstract = pick(row, CANDIDATE_ABSTRACT_COLUMNS)
        assignee = pick(row, CANDIDATE_ASSIGNEE_COLUMNS)
        published = pick(row, CANDIDATE_DATE_COLUMNS)
        patent_number = numeric_patent_number(document_number)
        permalink = ppubs_permalink(document_number)
        imported_at = now()

        con.execute(
            """INSERT INTO patents(
                document_number,patent_number,title,abstract,assignee,published,
                ppubs_permalink,source_file,source_sha256,imported_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(document_number) DO UPDATE SET
                title=excluded.title,
                abstract=excluded.abstract,
                assignee=excluded.assignee,
                published=excluded.published,
                ppubs_permalink=excluded.ppubs_permalink,
                source_file=excluded.source_file,
                source_sha256=excluded.source_sha256,
                imported_at=excluded.imported_at
            """,
            (
                document_number,
                patent_number,
                title,
                abstract,
                assignee,
                published,
                permalink,
                str(path),
                source_hash,
                imported_at,
            ),
        )
        con.execute("DELETE FROM patents_fts WHERE document_number=?", (document_number,))
        con.execute(
            "INSERT INTO patents_fts(document_number,title,abstract,assignee) VALUES(?,?,?,?)",
            (document_number, title, abstract, assignee),
        )
        imported += 1

    con.execute(
        """INSERT INTO source_artifacts(source_file,sha256,bytes,imported_rows,skipped_rows,imported_at)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(source_file) DO UPDATE SET
             sha256=excluded.sha256,
             bytes=excluded.bytes,
             imported_rows=excluded.imported_rows,
             skipped_rows=excluded.skipped_rows,
             imported_at=excluded.imported_at
        """,
        (str(path), source_hash, path.stat().st_size, imported, skipped, now()),
    )
    con.commit()
    return {
        "source_file": str(path),
        "sha256": source_hash,
        "bytes": path.stat().st_size,
        "imported_rows": imported,
        "skipped_rows": skipped,
    }


def write_manifest(con: sqlite3.Connection, output: Path, expected_manifest: Path | None) -> dict[str, Any]:
    total = con.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
    artifacts = [
        {
            "source_file": row[0],
            "sha256": row[1],
            "bytes": row[2],
            "imported_rows": row[3],
            "skipped_rows": row[4],
            "imported_at": row[5],
        }
        for row in con.execute(
            "SELECT source_file,sha256,bytes,imported_rows,skipped_rows,imported_at FROM source_artifacts ORDER BY source_file"
        )
    ]
    complete = False
    expected: list[dict[str, Any]] = []
    if expected_manifest:
        expected_data = json.loads(expected_manifest.read_text(encoding="utf-8"))
        expected = list(expected_data.get("artifacts") or [])
        actual_by_name = {Path(a["source_file"]).name: a for a in artifacts}
        complete = bool(expected) and all(
            item.get("filename") in actual_by_name
            and (
                not item.get("sha256")
                or actual_by_name[item["filename"]]["sha256"] == item["sha256"]
            )
            for item in expected
        )

    manifest = {
        "schema": "xunia.uspto-bulk-memory.v1",
        "generated_at": now(),
        "database": str(output / "uspto-bulk-memory.sqlite3"),
        "patent_records_indexed": total,
        "source_artifacts": artifacts,
        "expected_artifacts": expected,
        "complete_for_expected_manifest": complete,
        "all_uspto_patents_claimed": False,
        "completion_rule": (
            "This importer indexes supplied official bulk artifacts. "
            "It must not claim every USPTO patent is present unless an authoritative expected manifest "
            "defines the intended corpus and every artifact passes hash/import reconciliation."
        ),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def search(db_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    con = sqlite3.connect(db_path)
    rows = con.execute(
        """SELECT p.document_number,p.title,p.assignee,p.published,p.ppubs_permalink
           FROM patents_fts f JOIN patents p ON p.document_number=f.document_number
           WHERE patents_fts MATCH ? LIMIT ?""",
        (query, max(1, min(limit, 100))),
    ).fetchall()
    con.close()
    return [
        {
            "document_number": row[0],
            "title": row[1],
            "assignee": row[2],
            "published": row[3],
            "ppubs_permalink": row[4],
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-uspto-bulk-memory")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("files", nargs="+", type=Path)
    ingest.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".config/gpt-doug/uspto-bulk-memory",
    )
    ingest.add_argument("--expected-manifest", type=Path)

    search_cmd = sub.add_parser("search")
    search_cmd.add_argument("query")
    search_cmd.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".config/gpt-doug/uspto-bulk-memory",
    )
    search_cmd.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    db_path = output / "uspto-bulk-memory.sqlite3"

    if args.command == "ingest":
        con = initialize(db_path)
        reports = []
        for path in args.files:
            reports.append(import_file(con, path.expanduser()))
        manifest = write_manifest(con, output, args.expected_manifest)
        con.close()
        print(json.dumps({"imports": reports, "manifest": manifest}, indent=2))
        return 0

    if args.command == "search":
        if not db_path.is_file():
            raise SystemExit(f"bulk memory database not found: {db_path}")
        print(json.dumps(search(db_path, args.query, args.limit), indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
