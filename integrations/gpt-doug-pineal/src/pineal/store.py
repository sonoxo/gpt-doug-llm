"""Local-only, ontology-first SQLite memory with tamper-evident audit entries."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

_SECRET = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"(?:api[_-]?key|password)\s*[:=]\s*[^\s]{8,}|"
    r"bearer\s+[A-Za-z0-9._~+/-]{16,})", re.IGNORECASE
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_text(name: str, value: Any, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be non-empty text of at most {maximum} characters")
    if "\x00" in value:
        raise ValueError(f"{name} contains NUL")
    if _SECRET.search(value):
        raise ValueError(f"{name} appears to contain a credential")
    return value.strip()


class ConflictError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


class PinealStore:
    """Memory records are external AI state, NOT hidden model weights or chain of thought.

    Every mutation and telemetry decision is committed together with an audit hash.
    Audit entries intentionally omit memory plaintext. Back up the database safely.
    """

    def __init__(self, database: str | Path):
        self.path = Path(database).expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(fd)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL, subject TEXT NOT NULL,
                    predicate TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL,
                    confidence REAL NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, expires_at TEXT,
                    version INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_mem_subject ON memories(namespace, subject);
                CREATE INDEX IF NOT EXISTS idx_mem_expiry ON memories(expires_at);
                CREATE TABLE IF NOT EXISTS audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, stamp TEXT NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, entity TEXT NOT NULL,
                    detail TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, stamp TEXT NOT NULL,
                    temperature_c REAL NOT NULL, power_w REAL NOT NULL,
                    water_fraction REAL NOT NULL, mode TEXT NOT NULL,
                    rationale TEXT NOT NULL
                );
            """)

    @staticmethod
    def _append_audit(db: sqlite3.Connection, actor: str, action: str,
                      entity: str, detail: dict[str, Any]) -> None:
        previous = db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous_hash = previous["hash"] if previous else "0" * 64
        stamp = utcnow()
        detail_text = json.dumps(detail, sort_keys=True, separators=(",", ":"))
        material = json.dumps([stamp, actor, action, entity, detail_text, previous_hash],
                              separators=(",", ":"))
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        db.execute("INSERT INTO audit(stamp, actor, action, entity, detail, previous_hash, hash) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (stamp, actor, action, entity, detail_text, previous_hash, digest))

    def put(self, *, subject: str, predicate: str, value: str,
            namespace: str = "general", source: str = "user", confidence: float = 1.0,
            ttl_seconds: int | None = None, actor: str = "local",
            item_id: str | None = None, expected_version: int | None = None) -> dict[str, Any]:
        fields = {
            "namespace": validate_text("namespace", namespace, 96),
            "subject": validate_text("subject", subject, 256),
            "predicate": validate_text("predicate", predicate, 128),
            "value": validate_text("value", value, 8192),
            "source": validate_text("source", source, 512),
            "actor": validate_text("actor", actor, 80),
        }
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be a finite number between 0 and 1")
        if ttl_seconds is not None and (type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 31536000):
            raise ValueError("ttl_seconds must be an integer from 1 to 31536000")
        if item_id is not None and (expected_version is None or type(expected_version) is not int or expected_version < 1):
            raise ConflictError("updating requires expected_version >= 1")
        now = utcnow()
        expiration = ((datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds))
                      .isoformat(timespec="seconds") if ttl_seconds else None)
        new_id = item_id or str(uuid.uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if item_id:
                existing = db.execute("SELECT version FROM memories WHERE id=?", (item_id,)).fetchone()
                if existing is None:
                    raise NotFoundError("memory not found")
                if existing["version"] != expected_version:
                    raise ConflictError("memory version mismatch")
                db.execute("UPDATE memories SET namespace=?, subject=?, predicate=?, value=?, "
                           "source=?, confidence=?, updated_at=?, expires_at=?, version=version+1 "
                           "WHERE id=?", (fields["namespace"], fields["subject"],
                           fields["predicate"], fields["value"], fields["source"],
                           float(confidence), now, expiration, new_id))
                version = expected_version + 1
                action = "update"
            else:
                db.execute("INSERT INTO memories(id, namespace, subject, predicate, value, source, "
                           "confidence, created_at, updated_at, expires_at, version) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                           (new_id, fields["namespace"], fields["subject"],
                            fields["predicate"], fields["value"], fields["source"],
                            float(confidence), now, now, expiration))
                version = 1
                action = "create"
            self._append_audit(db, fields["actor"], action, new_id,
                               {"namespace": fields["namespace"], "version": version})
        return self.get(new_id)

    def get(self, item_id: str) -> dict[str, Any]:
        with self._connect() as db:
            record = db.execute("SELECT * FROM memories WHERE id=? AND "
                                "(expires_at IS NULL OR expires_at > ?)",
                                (item_id, utcnow())).fetchone()
            if record is None:
                raise NotFoundError("memory not found")
            return dict(record)

    def search(self, *, query: str = "", namespace: str | None = None,
               subject: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be from 1 to 100")
        if len(query) > 256:
            raise ValueError("query too long")
        clauses = ["(expires_at IS NULL OR expires_at > ?)"]
        args: list[Any] = [utcnow()]
        if namespace is not None:
            clauses.append("namespace = ?")
            args.append(validate_text("namespace", namespace, 96))
        if subject is not None:
            clauses.append("subject = ?")
            args.append(validate_text("subject", subject, 256))
        if query.strip():
            clauses.append("(instr(lower(subject), lower(?)) > 0 OR "
                           "instr(lower(predicate), lower(?)) > 0 OR "
                           "instr(lower(value), lower(?)) > 0)")
            args.extend([query.strip()] * 3)
        args.append(limit)
        statement = "SELECT * FROM memories WHERE " + " AND ".join(clauses) + " ORDER BY updated_at DESC, rowid DESC LIMIT ?"
        with self._connect() as db:
            return [dict(r) for r in db.execute(statement, args).fetchall()]

    def delete(self, item_id: str, *, expected_version: int, actor: str = "local") -> None:
        actor = validate_text("actor", actor, 80)
        if type(expected_version) is not int or expected_version < 1:
            raise ConflictError("deleting requires expected_version >= 1")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT version, namespace FROM memories WHERE id=?", (item_id,)).fetchone()
            if row is None:
                raise NotFoundError("memory not found")
            if row["version"] != expected_version:
                raise ConflictError("memory version mismatch")
            db.execute("DELETE FROM memories WHERE id=?", (item_id,))
            self._append_audit(db, actor, "delete", item_id,
                               {"namespace": row["namespace"], "version": expected_version})

    def verify_audit(self) -> dict[str, Any]:
        previous_hash = "0" * 64
        count = 0
        with self._connect() as db:
            rows = db.execute("SELECT * FROM audit ORDER BY seq").fetchall()
            for row in rows:
                material = json.dumps([row["stamp"], row["actor"], row["action"], row["entity"],
                                       row["detail"], previous_hash], separators=(",", ":"))
                expected = hashlib.sha256(material.encode("utf-8")).hexdigest()
                if row["previous_hash"] != previous_hash or row["hash"] != expected:
                    return {"ok": False, "checked": count, "failure_seq": row["seq"]}
                previous_hash = row["hash"]
                count += 1
        return {"ok": True, "checked": count, "head": previous_hash}

    def record_telemetry(self, *, temperature_c: float, power_w: float,
                         water_fraction: float, mode: str, rationale: str,
                         actor: str = "local") -> dict[str, Any]:
        values = (temperature_c, power_w, water_fraction)
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("telemetry values must be finite numbers")
        if not (-40 <= temperature_c <= 160 and 0 <= power_w <= 100000 and 0 <= water_fraction <= 1):
            raise ValueError("telemetry values outside expected ranges")
        actor = validate_text("actor", actor, 80)
        stamp = utcnow()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("INSERT INTO telemetry(stamp,temperature_c,power_w,water_fraction,mode,rationale) "
                                "VALUES (?,?,?,?,?,?)",
                                (stamp, temperature_c, power_w, water_fraction, mode, rationale))
            seq = cursor.lastrowid
            self._append_audit(db, actor, "telemetry_advisory", str(seq), {"mode": mode})
        return {"seq": seq, "stamp": stamp, "mode": mode, "rationale": rationale,
                "actuated": False}

    def latest_telemetry(self) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM telemetry ORDER BY seq DESC LIMIT 1").fetchone()
            return dict(row) if row else None

    def heartbeat(self) -> dict[str, Any]:
        """Prune expired memory; no external activity or background execution."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            expired = db.execute("SELECT id FROM memories WHERE expires_at IS NOT NULL "
                                 "AND expires_at <= ?", (utcnow(),)).fetchall()
            db.execute("DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                       (utcnow(),))
            self._append_audit(db, "heartbeat", "expire", "memories", {"count": len(expired)})
        return {"expired": len(expired), "at": utcnow()}
