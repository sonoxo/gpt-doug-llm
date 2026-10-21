"""GPT-Doug BioChip: local-first, provenance-aware durable agent memory.

Software architecture only; does not interface with biological tissue or hardware.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

class BioChip:
    def __init__(self, database: str = "biochip.sqlite3"):
        self.database = str(database)
        self.lock = threading.RLock()
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    visibility TEXT NOT NULL CHECK(visibility IN ('private','shared')),
                    owner TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL,
                    digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    actor TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    key TEXT NOT NULL,
                    outcome TEXT NOT NULL
                );
            """)

    @contextmanager
    def _connection(self):
        with self.lock:
            db = sqlite3.connect(self.database, timeout=10)
            try:
                db.execute("PRAGMA busy_timeout=10000")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    @staticmethod
    def _validate_actor(actor: str) -> None:
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a nonempty string")

    def _audit(self, db, actor: str, operation: str, key: str, outcome: str):
        db.execute("INSERT INTO audit(timestamp,actor,operation,key,outcome) VALUES(?,?,?,?,?)",
                   (time.time(), actor, operation, key, outcome))

    def remember(self, key: str, value: Any, *, actor: str,
                 provenance: str, confidence: float = 1.0,
                 visibility: str = "private", ttl_seconds: float | None = None) -> None:
        self._validate_actor(actor)
        if not isinstance(key, str) or not key.strip() or not isinstance(provenance, str) or not provenance.strip():
            raise ValueError("key and provenance must be nonempty")
        if visibility not in ("private", "shared") or not (0 <= confidence <= 1):
            raise ValueError("invalid visibility or confidence")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        payload = json.dumps(value, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        now = time.time()
        with self._connection() as db:
            existing = db.execute("SELECT owner FROM memories WHERE key=?", (key,)).fetchone()
            if existing and existing[0] != actor:
                self._audit(db, actor, "remember", key, "denied")
                raise PermissionError("only the owner can replace a memory")
            db.execute("""INSERT INTO memories
                (key,value,provenance,confidence,visibility,owner,updated_at,expires_at,digest)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                value=excluded.value, provenance=excluded.provenance,
                confidence=excluded.confidence, visibility=excluded.visibility,
                updated_at=excluded.updated_at, expires_at=excluded.expires_at, digest=excluded.digest""",
                (key,payload,provenance,confidence,visibility,actor,now,
                 now + ttl_seconds if ttl_seconds else None,digest))
            self._audit(db,actor,"remember",key,"ok")

    def recall(self, key: str, *, actor: str) -> dict[str, Any] | None:
        self._validate_actor(actor)
        with self._connection() as db:
            row = db.execute("""SELECT value,provenance,confidence,visibility,owner,
                                      updated_at,expires_at,digest
                                FROM memories WHERE key=?""", (key,)).fetchone()
            if not row:
                self._audit(db,actor,"recall",key,"missing")
                return None
            value, provenance, confidence, visibility, owner, updated, expiry, digest = row
            if owner != actor and visibility != "shared":
                self._audit(db,actor,"recall",key,"denied")
                raise PermissionError("memory is private")
            if expiry is not None and expiry <= time.time():
                self._audit(db,actor,"recall",key,"expired")
                return None
            if hashlib.sha256(value.encode("utf-8")).hexdigest() != digest:
                self._audit(db,actor,"recall",key,"integrity_error")
                raise ValueError("memory integrity check failed")
            self._audit(db,actor,"recall",key,"ok")
            return {"key": key, "value": json.loads(value), "provenance": provenance,
                    "confidence": confidence, "visibility": visibility, "owner": owner,
                    "updated_at": updated, "expires_at": expiry}

    def forget(self, key: str, *, actor: str) -> bool:
        self._validate_actor(actor)
        with self._connection() as db:
            existing = db.execute("SELECT owner FROM memories WHERE key=?", (key,)).fetchone()
            if existing and existing[0] != actor:
                self._audit(db,actor,"forget",key,"denied")
                raise PermissionError("only the owner can delete a memory")
            removed = db.execute("DELETE FROM memories WHERE key=? AND owner=?", (key,actor)).rowcount > 0
            self._audit(db,actor,"forget",key,"ok" if removed else "missing")
            return removed

    def heartbeat(self, *, purge_expired: bool = True) -> dict[str, Any]:
        now = time.time()
        with self._connection() as db:
            expired = db.execute("SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?", (now,)).fetchone()[0]
            purged = db.execute("DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?", (now,)).rowcount if purge_expired else 0
            active = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            audit_events = db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
            ok = db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        return {"status": "healthy" if ok else "degraded", "timestamp": now,
                "active_memories": active, "expired_found": expired,
                "purged": purged, "audit_events": audit_events}

    def audit_trail(self, *, actor: str, limit: int = 100) -> list[dict[str, Any]]:
        self._validate_actor(actor)
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connection() as db:
            rows = db.execute("""SELECT timestamp,actor,operation,key,outcome FROM audit
                                 WHERE actor=? ORDER BY id DESC LIMIT ?""", (actor,limit)).fetchall()
        return [dict(zip(("timestamp","actor","operation","key","outcome"),row)) for row in rows]
