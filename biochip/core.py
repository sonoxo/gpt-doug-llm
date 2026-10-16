"""Transactional, provenance-aware, file-backed memory for trusted local callers."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from contextlib import closing
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any

from .validation import bounded_int, bounded_text, encode_json, finite_number
from .storage import prepare_file, file_path, reserve_file, connect_private

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS memories (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, provenance TEXT NOT NULL,
        confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
        visibility TEXT NOT NULL CHECK(visibility IN ('private','shared')),
        owner TEXT NOT NULL, updated_at REAL NOT NULL, expires_at REAL, digest TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL,
        actor TEXT NOT NULL, operation TEXT NOT NULL, key TEXT NOT NULL, outcome TEXT NOT NULL)""",
)


class BioChip:
    def __init__(self, database: str = 'biochip.sqlite3'):
        self.database = str(prepare_file(database))
        self.lock = threading.RLock()
        with self._connection() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('unsupported BioChip schema version')
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if not tables and version == 0:
                for statement in SCHEMA:
                    db.execute(statement)
            else:
                self._validate_schema(db, tables)
                self._validate_rows(db)
                if version == 0:
                    destination = self.database + '.legacy-v0-' + uuid.uuid4().hex + '.sqlite3'
                    self.backup(destination)
            if version == 0:
                db.execute('PRAGMA user_version=1')

    @staticmethod
    def _validate_schema(db, tables) -> None:
        expected = {
            'memories': [('key', 'TEXT'), ('value', 'TEXT'), ('provenance', 'TEXT'),
                         ('confidence', 'REAL'), ('visibility', 'TEXT'), ('owner', 'TEXT'),
                         ('updated_at', 'REAL'), ('expires_at', 'REAL'), ('digest', 'TEXT')],
            'audit': [('id', 'INTEGER'), ('timestamp', 'REAL'), ('actor', 'TEXT'),
                      ('operation', 'TEXT'), ('key', 'TEXT'), ('outcome', 'TEXT')],
        }
        if tables != set(expected) or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():
            raise ValueError('incompatible BioChip schema')
        for table, columns in expected.items():
            info = list(db.execute('PRAGMA table_info(' + table + ')'))
            actual = [(r[1], r[2].upper()) for r in info]
            keys = [r[5] for r in info]
            nullable = [r[1] for r in info if not r[3]]
            allowed_nullable = ['key', 'expires_at'] if table == 'memories' else ['id']
            if actual != columns or keys != [1] + [0] * (len(columns)-1) or nullable != allowed_nullable:
                raise ValueError('incompatible BioChip schema')

    @staticmethod
    def _validate_rows(db) -> None:
        for key, value, provenance, confidence, visibility, owner, updated, expiry, digest in db.execute('SELECT * FROM memories'):
            try:
                bounded_text(key, name='key', max_bytes=256)
                bounded_text(owner, name='owner', max_bytes=256)
                bounded_text(provenance, name='provenance', max_bytes=4096)
                finite_number(confidence, name='confidence', minimum=0, maximum=1)
                finite_number(updated, name='updated', minimum=0)
                if expiry is not None:
                    finite_number(expiry, name='expiry', minimum=0)
                if visibility not in ('private', 'shared'):
                    raise ValueError('visibility')
                if not isinstance(value, str) or len(value.encode('utf-8')) > 1048576:
                    raise ValueError('value')
                encode_json(json.loads(value))
                if hashlib.sha256(value.encode('utf-8')).hexdigest() != digest:
                    raise ValueError('digest')
            except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
                raise ValueError('invalid stored memory for key ' + repr(key)[:270]) from exc

    def backup(self, destination: str) -> None:
        """Create a consistent private snapshot; never overwrite any existing path."""
        target = file_path(destination)
        info = reserve_file(target)
        try:
            deadline = time.monotonic() + 10
            def progress(status, remaining, total):
                if time.monotonic() > deadline:
                    raise TimeoutError('database backup deadline exceeded')
            with closing(connect_private(self.database, read_only=True)) as source:
                with closing(connect_private(target)) as output:
                    source.backup(output, pages=128, progress=progress, sleep=0.01)
                    if output.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise ValueError('backup integrity check failed')
            with open(target, 'rb') as stream:
                os.fsync(stream.fileno())
        except BaseException:
            try:
                now = target.lstat()
                if (now.st_dev, now.st_ino) == (info.st_dev, info.st_ino):
                    target.unlink()
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def _connection(self):
        with self.lock:
            db = connect_private(self.database)
            try:
                db.execute('PRAGMA busy_timeout=10000')
                db.execute('BEGIN IMMEDIATE')
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    @staticmethod
    def _validate_actor(actor: str) -> None:
        bounded_text(actor, name='actor', max_bytes=256)

    def _audit(self, db, actor: str, operation: str, key: str, outcome: str):
        db.execute('INSERT INTO audit(timestamp,actor,operation,key,outcome) VALUES(?,?,?,?,?)',
                   (time.time(), actor, operation, key, outcome))

    def remember(self, key: str, value: Any, *, actor: str, provenance: str,
                 confidence: float = 1.0, visibility: str = 'private',
                 ttl_seconds: float | None = None) -> None:
        self._validate_actor(actor)
        bounded_text(key, name='key', max_bytes=256)
        bounded_text(provenance, name='provenance', max_bytes=4096)
        confidence = finite_number(confidence, name='confidence', minimum=0, maximum=1)
        if visibility not in ('private', 'shared'):
            raise ValueError('invalid visibility')
        if ttl_seconds is not None:
            ttl_seconds = finite_number(ttl_seconds, name='ttl_seconds', minimum=0, exclusive_minimum=True)
        payload = encode_json(value).decode('utf-8')
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        now = finite_number(time.time(), name='timestamp', minimum=0)
        expiry = (finite_number(now + ttl_seconds, name='expiry', minimum=0)
                  if ttl_seconds is not None else None)
        denied = False
        with self._connection() as db:
            row = db.execute('SELECT owner FROM memories WHERE key=?', (key,)).fetchone()
            denied = row is not None and row[0] != actor
            if denied:
                self._audit(db, actor, 'remember', key, 'denied')
            else:
                db.execute('''INSERT INTO memories
                    (key,value,provenance,confidence,visibility,owner,updated_at,expires_at,digest)
                    VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value, provenance=excluded.provenance,
                    confidence=excluded.confidence, visibility=excluded.visibility,
                    updated_at=excluded.updated_at, expires_at=excluded.expires_at, digest=excluded.digest
                    WHERE memories.owner=excluded.owner''',
                    (key, payload, provenance, confidence, visibility, actor, now, expiry, digest))
                self._audit(db, actor, 'remember', key, 'ok')
        if denied:
            raise PermissionError('only the owner can replace a memory')

    def recall(self, key: str, *, actor: str) -> dict[str, Any] | None:
        self._validate_actor(actor)
        bounded_text(key, name='key', max_bytes=256)
        error = None
        result = None
        with self._connection() as db:
            row = db.execute('''SELECT value,provenance,confidence,visibility,owner,
                               updated_at,expires_at,digest FROM memories WHERE key=?''', (key,)).fetchone()
            if row is None:
                outcome = 'missing'
            else:
                value, provenance, confidence, visibility, owner, updated, expiry, digest = row
                if owner != actor and visibility != 'shared':
                    outcome, error = 'denied', PermissionError('memory is private')
                elif expiry is not None and expiry <= time.time():
                    outcome = 'expired'
                else:
                    try:
                        if hashlib.sha256(value.encode('utf-8')).hexdigest() != digest:
                            raise ValueError('digest mismatch')
                        decoded = json.loads(value)
                        encode_json(decoded)
                    except (ValueError, TypeError, UnicodeError, RecursionError, AttributeError):
                        outcome, error = 'integrity_error', ValueError('memory integrity check failed')
                    else:
                        outcome = 'ok'
                        result = dict(key=key, value=decoded, provenance=provenance, confidence=confidence,
                                      visibility=visibility, owner=owner, updated_at=updated, expires_at=expiry)
            self._audit(db, actor, 'recall', key, outcome)
        if error is not None:
            raise error
        return result

    def forget(self, key: str, *, actor: str) -> bool:
        self._validate_actor(actor)
        bounded_text(key, name='key', max_bytes=256)
        removed, denied = False, False
        with self._connection() as db:
            row = db.execute('SELECT owner FROM memories WHERE key=?', (key,)).fetchone()
            denied = row is not None and row[0] != actor
            if denied:
                outcome = 'denied'
            else:
                removed = db.execute('DELETE FROM memories WHERE key=? AND owner=?', (key, actor)).rowcount > 0
                outcome = 'ok' if removed else 'missing'
            self._audit(db, actor, 'forget', key, outcome)
        if denied:
            raise PermissionError('only the owner can delete a memory')
        return removed

    def heartbeat(self, *, purge_expired: bool = True) -> dict[str, Any]:
        now = time.time()
        with self._connection() as db:
            expired = db.execute('SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?', (now,)).fetchone()[0]
            purged = db.execute('DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?', (now,)).rowcount if purge_expired else 0
            active = db.execute('SELECT COUNT(*) FROM memories').fetchone()[0]
            audit_events = db.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
            ok = db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        return dict(status='healthy' if ok else 'degraded', timestamp=now, active_memories=active,
                    expired_found=expired, purged=purged, audit_events=audit_events)

    def audit_trail(self, *, actor: str, limit: int = 100) -> list[dict[str, Any]]:
        self._validate_actor(actor)
        bounded_int(limit, name='limit', minimum=1, maximum=1000)
        with self._connection() as db:
            rows = db.execute('''SELECT timestamp,actor,operation,key,outcome FROM audit
                                 WHERE actor=? ORDER BY id DESC LIMIT ?''', (actor, limit)).fetchall()
        return [dict(zip(('timestamp', 'actor', 'operation', 'key', 'outcome'), row)) for row in rows]
