"""GPT-DOUG Dataset Civilization: governed local-first, resumable dataset pipeline.

Zero external dependencies, zero paid APIs, zero background network access.
Five logical stages: discover -> validate -> index -> relate -> audit.
The roles are deterministic processors, not independent LLM agents.
"""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "gpt-doug.dataset-fleet.manifest.v1"
MAX_BYTES = 8_000_000
MAX_RECORDS = 10_000
MAX_RECORD_BYTES = 25_000
MAX_WORKERS = 8
ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
FORBIDDEN_PARTS = {"private", "secret", "secrets", ".ssh", ".aws", ".env", "credentials", "token", "tokens", ".git", "node_modules", "venv", ".venv"}
FORMAT_SUFFIX = {"json": ".json", "jsonl": ".jsonl", "csv": ".csv"}


class FleetError(ValueError):
    """Dataset failed a governance or schema gate."""


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_path(root: Path, relative: str, kind: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise FleetError("unsafe relative path")
    p = PurePosixPath(relative)
    if p.is_absolute() or any(x in ("", ".", "..") for x in p.parts):
        raise FleetError("path must be explicitly relative to the approved repository")
    if any(x.lower() in FORBIDDEN_PARTS or x.lower().startswith(".env") for x in p.parts):
        raise FleetError("restricted path segment")
    if kind not in FORMAT_SUFFIX or p.suffix.lower() != FORMAT_SUFFIX[kind]:
        raise FleetError("unexpected dataset format or extension")
    root = root.resolve(strict=True)
    target = root.joinpath(*p.parts)
    if any(x.is_symlink() for x in (target, *target.parents) if x != root and root in x.parents):
        raise FleetError("symlink traversal forbidden")
    target = target.resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise FleetError("dataset outside authorized repository")
    if target.stat().st_size > MAX_BYTES:
        raise FleetError("dataset exceeds maximum bytes")
    return target


def manifest_from_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise FleetError("invalid dataset-fleet manifest")
    sources = data.get("datasets")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise FleetError("manifest requires 1 to 100 explicitly selected datasets")
    seen = set()
    for s in sources:
        if not isinstance(s, dict) or not ID_RE.fullmatch(str(s.get("id", ""))):
            raise FleetError("invalid dataset identifier")
        if s["id"] in seen:
            raise FleetError("duplicate dataset ID")
        seen.add(s["id"])
        if s.get("sensitivity") != "public" or s.get("approved") is not True:
            raise FleetError("nonpublic or unapproved dataset refused")
        if s.get("format") not in FORMAT_SUFFIX:
            raise FleetError("unsupported dataset format")
        if not isinstance(s.get("path"), str):
            raise FleetError("missing dataset path")
        if not isinstance(s.get("provenance"), str) or not s["provenance"].startswith("https://github.com/sonoxo/"):
            raise FleetError("unverified source provenance")
        if s.get("rows_key") is not None and (not isinstance(s["rows_key"], str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", s["rows_key"])):
            raise FleetError("invalid root-level row selector")
        if not isinstance(s.get("related_to", []), list):
            raise FleetError("related_to must be a list")
        for target in s.get("related_to", []):
            if not isinstance(target, str) or not ID_RE.fullmatch(target):
                raise FleetError("invalid relation target")
    for s in sources:
        if any(t not in seen or t == s["id"] for t in s.get("related_to", [])):
            raise FleetError("unknown or self-referential lineage target")
    return data


def _records(raw: bytes, source: dict) -> list[dict[str, Any]]:
    fmt = source["format"]
    txt = raw.decode("utf-8-sig")
    if fmt == "json":
        obj = json.loads(txt)
        if source.get("rows_key"):
            if not isinstance(obj, dict) or not isinstance(obj.get(source["rows_key"]), list):
                raise FleetError("expected root-level array " + source["rows_key"])
            records = obj[source["rows_key"]]
        elif isinstance(obj, list):
            records = obj
        else:
            records = [obj]
    elif fmt == "jsonl":
        records = [json.loads(line) for line in txt.splitlines() if line.strip()]
    else:
        records = list(csv.DictReader(txt.splitlines()))
    if not 1 <= len(records) <= MAX_RECORDS:
        raise FleetError("dataset record count outside approved bounds")
    cleaned = []
    for record in records:
        if not isinstance(record, dict):
            raise FleetError("record must be an object")
        record_str = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(record_str.encode("utf-8")) > MAX_RECORD_BYTES:
            raise FleetError("record exceeds maximum size")
        cleaned.append(record)
    return cleaned


def _process(root: Path, source: dict) -> dict:
    path = safe_path(root, source["path"], source["format"])
    # Enforce bound while reading; do not follow a changed symlink.
    with path.open("rb") as fp:
        raw = fp.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise FleetError("dataset exceeds byte limit")
    records = _records(raw, source)
    digest = hashlib.sha256(raw).hexdigest()
    keys = sorted({str(k) for r in records for k in r})
    nulls = {k: sum(r.get(k) is None or r.get(k) == "" for r in records) for k in keys}
    return {"id": source["id"], "sha256": digest, "bytes": len(raw),
            "rows": records, "schemaFields": keys[:300], "missingValues": nulls}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS jobs(
      dataset_id TEXT PRIMARY KEY, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS datasets(
      id TEXT PRIMARY KEY, path TEXT NOT NULL, checksum TEXT NOT NULL,
      bytes INTEGER NOT NULL, rows INTEGER NOT NULL, schema_json TEXT NOT NULL,
      missing_json TEXT NOT NULL, provenance TEXT NOT NULL,
      updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS records(
      dataset_id TEXT NOT NULL, position INTEGER NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(dataset_id,position), FOREIGN KEY(dataset_id) REFERENCES datasets(id));
    CREATE TABLE IF NOT EXISTS lineage(
      source_id TEXT NOT NULL, target_id TEXT NOT NULL, kind TEXT NOT NULL,
      PRIMARY KEY(source_id,target_id,kind));
    CREATE TABLE IF NOT EXISTS audits(
      id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
      dataset_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL);
    """)
    return con


def audit(con: sqlite3.Connection, dataset_id: str | None, event: str, detail: dict) -> None:
    con.execute("INSERT INTO audits(ts,dataset_id,event,detail) VALUES(?,?,?,?)",
                (utc(), dataset_id, event, json.dumps(detail, sort_keys=True)))


def run(root: Path, manifest_path: Path, db_path: Path, workers: int = 4, max_attempts: int = 3) -> dict:
    """Resumable deterministic fleet; each file is an independently recoverable job."""
    if not 1 <= workers <= MAX_WORKERS or not 1 <= max_attempts <= 5:
        raise FleetError("workers must be 1-8; retry budget 1-5")
    root = Path(root).resolve(strict=True)
    manifest_path = Path(manifest_path)
    # Do not permit an attacker-supplied manifest from outside the approved root.
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    mp = manifest_path.resolve(strict=True)
    if not mp.is_relative_to(root) or mp.suffix != ".json" or mp.is_symlink():
        raise FleetError("manifest must be an approved repository JSON file")
    data = manifest_from_file(mp)
    sources = data["datasets"]
    for source in sources:
        safe_path(root, source["path"], source["format"])
    con = connect(db_path)
    try:
        with con:
            for s in sources:
                row = con.execute("SELECT status FROM jobs WHERE dataset_id=?", (s["id"],)).fetchone()
                if row is None:
                    con.execute("INSERT INTO jobs(dataset_id,status,updated_at) VALUES(?,?,?)",
                                (s["id"], "queued", utc()))
                else:
                    # Restart cleanly; never leave a permanently stuck in-progress job.
                    con.execute("UPDATE jobs SET status='queued',attempts=0,last_error=NULL,updated_at=? WHERE dataset_id=?",
                                (utc(), s["id"]))
            audit(con, None, "fleet_started", {"datasets": len(sources), "workers": workers, "network": False})
        # Parallelize only independent local reads and validation; SQL writes stay serialized.
        pending = list(sources)
        for attempt in range(1, max_attempts + 1):
            if not pending:
                break
            retry = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gpt-doug-dataset") as pool:
                futures = {pool.submit(_process, root, s): s for s in pending}
                for future in concurrent.futures.as_completed(futures):
                    s = futures[future]
                    try:
                        result = future.result()
                        with con:
                            prior = con.execute("SELECT checksum FROM datasets WHERE id=?", (s["id"],)).fetchone()
                            if prior is not None and prior["checksum"] == result["sha256"]:
                                con.execute("UPDATE jobs SET status='unchanged',attempts=?,last_error=NULL,updated_at=? WHERE dataset_id=?",
                                            (attempt, utc(), s["id"]))
                                audit(con, s["id"], "idempotent_skip", {"sha256": result["sha256"]})
                                continue
                            con.execute("""INSERT INTO datasets(id,path,checksum,bytes,rows,schema_json,missing_json,provenance,updated_at)
                                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                                path=excluded.path,checksum=excluded.checksum,bytes=excluded.bytes,rows=excluded.rows,
                                schema_json=excluded.schema_json,missing_json=excluded.missing_json,
                                provenance=excluded.provenance,updated_at=excluded.updated_at""",
                                (s["id"], s["path"], result["sha256"], result["bytes"], len(result["rows"]),
                                 json.dumps(result["schemaFields"]), json.dumps(result["missingValues"]),
                                 s["provenance"], utc()))
                            con.execute("DELETE FROM records WHERE dataset_id=?", (s["id"],))
                            con.executemany("INSERT INTO records(dataset_id,position,payload) VALUES(?,?,?)",
                                ((s["id"], i, json.dumps(row, ensure_ascii=False, sort_keys=True)) for i,row in enumerate(result["rows"])))
                            con.execute("UPDATE jobs SET status='completed',attempts=?,last_error=NULL,updated_at=? WHERE dataset_id=?",
                                        (attempt, utc(), s["id"]))
                            audit(con, s["id"], "dataset_indexed", {"rows": len(result["rows"]), "sha256": result["sha256"]})
                    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error, FleetError, TypeError, ValueError) as exc:
                        transient = isinstance(exc, OSError) and not isinstance(exc, FleetError)
                        status = "retry" if transient and attempt < max_attempts else "quarantined"
                        with con:
                            con.execute("UPDATE jobs SET status=?,attempts=?,last_error=?,updated_at=? WHERE dataset_id=?",
                                        (status, attempt, type(exc).__name__, utc(), s["id"]))
                            audit(con, s["id"], status, {"reason": type(exc).__name__, "attempt": attempt})
                        if status == "retry":
                            retry.append(s)
            pending = retry
            if pending:
                time.sleep(min(.2 * (2 ** (attempt-1)), 1.0))
        with con:
            # Rebuild only explicit catalog relations, never infer runtime dependencies.
            con.execute("DELETE FROM lineage")
            for s in sources:
                for target in s.get("related_to", []):
                    con.execute("INSERT OR IGNORE INTO lineage(source_id,target_id,kind) VALUES(?,?,?)",
                                (s["id"], target, "curated-reference"))
            audit(con, None, "fleet_completed", {"statuses": status_counts(con)})
        return report(con, data)
    finally:
        con.close()


def status_counts(con: sqlite3.Connection) -> dict[str, int]:
    return {row["status"]: row["n"] for row in
            con.execute("SELECT status,COUNT(*) n FROM jobs GROUP BY status")}


def report(con: sqlite3.Connection, manifest: dict | None = None) -> dict:
    sources = (manifest or {}).get("datasets", [])
    labels = {s["id"]: s for s in sources}
    datasets = []
    for row in con.execute("SELECT * FROM datasets ORDER BY id"):
        item = {"id": row["id"], "rows": row["rows"], "bytes": row["bytes"],
                "sha256": row["checksum"], "fields": json.loads(row["schema_json"]),
                "missingValues": json.loads(row["missing_json"]),
                "provenance": row["provenance"], "indexedAt": row["updated_at"]}
        if row["id"] in labels:
            item["name"] = labels[row["id"]].get("name", row["id"])
            item["category"] = labels[row["id"]].get("category", "public-metadata")
        datasets.append(item)
    lineage = [dict(row) for row in con.execute("SELECT source_id,target_id,kind FROM lineage ORDER BY source_id,target_id")]
    return {"schema": "gpt-doug.dataset-fleet.report.v1", "generatedAt": utc(),
            "runtime": "local-stdlib-sqlite", "networkAccess": False, "modelAPICalls": 0,
            "agents": [{"name": n, "type": "deterministic-local-role"} for n in
                       ["DISCOVER", "VERIFY", "INDEX", "RELATE", "AUDIT"]],
            "statuses": status_counts(con), "datasets": datasets, "lineage": lineage,
            "summary": {"datasets": len(datasets),
                        "rows": sum(d["rows"] for d in datasets),
                        "related": len(lineage)},
            "warnings": ["Dataset relationships are curated references, not verified runtime dependencies.",
                         "No live external collection, vulnerability scanning or automatic self-replication."]}


def search(con: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    if not 2 <= len(query) <= 100 or not 1 <= limit <= 50:
        raise FleetError("search query length 2-100; limit 1-50")
    # Escape SQLite LIKE wildcards to prevent wild-carded full collection enumeration.
    needle = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = con.execute("""SELECT dataset_id,position,payload FROM records
        WHERE LOWER(payload) LIKE ? ESCAPE '\\' ORDER BY dataset_id,position LIMIT ?""",
        ("%" + needle + "%", limit)).fetchall()
    return [{"dataset": row["dataset_id"], "record": row["position"],
             "excerpt": row["payload"][:350]} for row in rows]
