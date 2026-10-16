"""Private metadata-only mission history; uncertain work is never replayed."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import time
from typing import Any
import uuid

from .config import FleetConfig
from ..storage import file_path, private_directory, prepare_file, connect_private
from ..validation import bounded_int, bounded_text, decode_json, encode_json, finite_number

POLICY_REVISION = 'kraken-local-proposal-v1'
TRANSITIONS = {
    'queued': {'running', 'stopped', 'uncertain'},
    'running': {'completed', 'failed', 'stopped', 'uncertain'},
}
REASONS = {'abandoned', 'provider_failure', 'deadline_exceeded', 'operator_stop',
           'budget_exceeded', 'validation_failure', 'worker_failure', 'storage_failure',
           'missing_model', 'reviewed_proposal', 'no_reviewer', 'inference_dispatched', 'inference_completed'}


def source_revision() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    sources = sorted(p for p in root.rglob('*.py') if 'tests' not in p.relative_to(root).parts)
    sources.append(root.parent / 'ai_killswitch.py')
    for path in sources:
        name = str(path.relative_to(root.parent)).encode('utf-8')
        data = path.read_bytes()
        digest.update(name + b'\0' + str(len(data)).encode() + b'\0' + data)
    return 'sha256:' + digest.hexdigest()


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError('event must be a metadata object')
    for key, value in event.items():
        if key in ('model_calls', 'tool_calls'):
            bounded_int(value, name=key, minimum=0, maximum=8 if key == 'model_calls' else 0)
        elif key == 'reported_output_tokens':
            if value is not None:
                bounded_int(value, name=key, minimum=0, maximum=2**63-1)
        elif key == 'elapsed_seconds':
            finite_number(value, name=key, minimum=0)
        elif key in ('provider', 'model', 'operator', 'project'):
            bounded_text(value, name=key, max_bytes=256)
        elif key in ('prompt_sha256', 'proposal_sha256', 'schema_sha256', 'artifact_sha256'):
            if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
                raise ValueError('invalid metadata digest')
        elif key == 'role':
            if value not in ('planner', 'reviewer'):
                raise ValueError('invalid worker role')
        elif key == 'reason':
            if value not in REASONS:
                raise ValueError('reason must be a defined code, not arbitrary text')
        elif key in ('inference_verified', 'review_verified', 'independent_models'):
            if value is not None and type(value) is not bool:
                raise ValueError('invalid verification flag')
        else:
            raise ValueError('unknown or sensitive event field')
    return decode_json(encode_json(event, max_bytes=65536), max_bytes=65536)


class MissionLedger:
    def __init__(self, database: Path, *, read_only: bool = False):
        self._read_only = read_only
        if not isinstance(database, (str, Path)):
            raise ValueError('ledger path must be text or a Path')
        # Check the supplied state directory before ancestor canonicalization.
        raw = Path(database).expanduser().absolute()
        private_directory(raw.parent, create=not read_only)
        path = file_path(raw)
        self._database = path if read_only else prepare_file(path)
        with self._connection(write=not read_only) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if version == 0 and not tables and not read_only:
                db.execute('''CREATE TABLE missions (id TEXT PRIMARY KEY, operator TEXT NOT NULL,
                    project TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL,
                    updated REAL NOT NULL, metadata TEXT NOT NULL)''')
                db.execute('''CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL REFERENCES missions(id), at REAL NOT NULL, data TEXT NOT NULL)''')
                db.execute('PRAGMA user_version=1')
            elif version != 1 or tables != {'missions', 'events'}:
                raise ValueError('unsupported or incompatible mission ledger schema')
            else:
                for table, names in (
                    ('missions', ['id', 'operator', 'project', 'state', 'created', 'updated', 'metadata']),
                    ('events', ['id', 'mission_id', 'at', 'data'])):
                    info = list(db.execute('PRAGMA table_info(' + table + ')'))
                    if [row[1] for row in info] != names or info[0][5] != 1:
                        raise ValueError('incompatible ledger columns')

    @property
    def database(self) -> Path:
        return self._database

    @contextmanager
    def _connection(self, *, write: bool):
        if write and self._read_only:
            raise PermissionError('ledger is read-only')
        db = connect_private(self.database, read_only=not write)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _id(mission_id: str) -> None:
        if not isinstance(mission_id, str) or not re.fullmatch('[0-9a-f]{32}', mission_id):
            raise ValueError('invalid mission identifier')

    def create(self, config: FleetConfig, prompt_sha256: str) -> str:
        validate_event({'prompt_sha256': prompt_sha256})
        if self.database != file_path(config.state_directory / 'missions.sqlite3'):
            raise ValueError('ledger does not match configured state directory')
        mid, now = uuid.uuid4().hex, time.time()
        metadata = dict(prompt_sha256=prompt_sha256, source_revision=source_revision(), policy_revision=POLICY_REVISION,
                        planner=dict(provider=config.planner.provider, model=config.planner.name),
                        reviewer=(dict(provider=config.reviewer.provider, model=config.reviewer.name) if config.reviewer else None),
                        model_calls=0, tool_calls=0, reported_output_tokens=None,
                        inference_verified=None, review_verified=None)
        with self._connection(write=True) as db:
            db.execute('INSERT INTO missions VALUES(?,?,?,?,?,?,?)',
                       (mid, config.operator, config.project, 'queued', now, now, encode_json(metadata).decode()))
            db.execute('INSERT INTO events(mission_id,at,data) VALUES(?,?,?)', (mid, now, '{}'))
        return mid

    def _record(self, db, mid: str, event: dict[str, Any]) -> None:
        row = db.execute('SELECT metadata FROM missions WHERE id=?', (mid,)).fetchone()
        if row is None:
            raise KeyError('unknown mission')
        metadata = decode_json(row[0].encode())
        metadata.update(event)
        now = time.time()
        db.execute('UPDATE missions SET metadata=?,updated=? WHERE id=?', (encode_json(metadata).decode(), now, mid))
        db.execute('INSERT INTO events(mission_id,at,data) VALUES(?,?,?)', (mid, now, encode_json(event).decode()))

    def transition(self, mission_id: str, *, expected: str, new: str, detail: dict[str, Any]) -> bool:
        self._id(mission_id)
        event = validate_event(detail)
        if new not in TRANSITIONS.get(expected, set()):
            return False
        with self._connection(write=True) as db:
            changed = db.execute('UPDATE missions SET state=?,updated=? WHERE id=? AND state=?',
                                 (new, time.time(), mission_id, expected)).rowcount
            if changed:
                self._record(db, mission_id, event)
        return bool(changed)

    def record(self, mission_id: str, event: dict[str, Any]) -> None:
        self._id(mission_id)
        validated = validate_event(event)
        with self._connection(write=True) as db:
            self._record(db, mission_id, validated)

    def read(self, mission_id: str, *, operator: str, project: str) -> dict[str, Any]:
        self._id(mission_id)
        with self._connection(write=False) as db:
            row = db.execute('SELECT operator,project,state,created,updated,metadata FROM missions WHERE id=?', (mission_id,)).fetchone()
            if row is None:
                raise KeyError('unknown mission')
            if (row[0], row[1]) != (operator, project):
                raise PermissionError('mission belongs to a different operator/project')
            events = db.execute('SELECT at,data FROM events WHERE mission_id=? ORDER BY id LIMIT 128', (mission_id,)).fetchall()
        return dict(id=mission_id, operator=row[0], project=row[1], state=row[2], created=row[3], updated=row[4],
                    metadata=decode_json(row[5].encode()), events=[dict(at=t, data=decode_json(d.encode())) for t, d in events])

    def reconcile_interrupted(self) -> int:
        """Caller must first acquire the supervisor lock; this never dispatches work."""
        with self._connection(write=True) as db:
            ids = [r[0] for r in db.execute("SELECT id FROM missions WHERE state IN ('queued','running')")]
            for mid in ids:
                db.execute("UPDATE missions SET state='uncertain' WHERE id=?", (mid,))
                self._record(db, mid, {'reason': 'abandoned'})
        return len(ids)
