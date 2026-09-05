"""Durable, project-scoped context for Black House humans and agents.

Memory records describe data, logic, actions, decisions and preferences. They
never grant execution authority, even when their declared source is human.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from uuid import uuid4

MEMORY_SCHEMA = "black-house.memory.v1"
MEMORY_KINDS = frozenset({"data", "logic", "action", "decision", "preference"})
MEMORY_SOURCES = frozenset({"human", "model", "imported"})
MAX_CONTENT_CHARS = 12_000
MAX_IMPORT_NOTES = 1_000
MAX_IMPORT_CHARS = 4_000_000
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:-]{0,199}\Z")
_FIELDS = ("id", "kind", "content", "source", "author", "created")


def _string(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string of at most {maximum} characters")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain null characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{name} must be valid Unicode") from error
    return value


def _note_id(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("memory id must contain 1-128 letters, digits, dots, underscores, colons or hyphens")
    return value


def _created(value: Any = None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    else:
        _string(value, "created", 64)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("created must be an ISO 8601 timestamp with a timezone") from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("created must include a timezone")
    try:
        return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (ValueError, OverflowError) as error:
        raise ValueError("created must resolve to a supported UTC timestamp") from error


def _record(
    kind: Any,
    content: Any,
    source: Any,
    author: Any,
    note_id: Any = None,
    created: Any = None,
) -> dict[str, Any]:
    if not isinstance(kind, str) or kind not in MEMORY_KINDS:
        raise ValueError(f"memory kind must be one of: {', '.join(sorted(MEMORY_KINDS))}")
    if not isinstance(source, str) or source not in MEMORY_SOURCES:
        raise ValueError(f"memory source must be one of: {', '.join(sorted(MEMORY_SOURCES))}")
    return {
        "id": _note_id(uuid4().hex if note_id is None else note_id),
        "kind": kind,
        "content": _string(content, "memory content", MAX_CONTENT_CHARS),
        "source": source,
        "author": _string(author, "memory author", 200),
        "created": _created(created),
    }


class ProjectMemory:
    """SQLite-backed shared context with an immutable scope per instance.

    A separate connection and transaction are used for each operation so that
    independent agents and processes can safely share the database. Hosts must
    choose the project scope from authenticated application state, never from
    untrusted model tool arguments.
    """

    def __init__(self, path: str | Path, project: str) -> None:
        if not isinstance(project, str) or not _PROJECT.fullmatch(project):
            raise ValueError("project must be a 1-200 character stable identifier without whitespace")
        if not isinstance(path, (str, Path)) or not str(path).strip() or str(path) == ":memory:":
            raise ValueError("memory requires a persistent database file path")
        self.path = Path(path).expanduser().resolve()
        self.project = project
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if not self.path.is_file():
                raise ValueError("memory database path must be a file")
        else:
            os.close(descriptor)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_notes (
                    project TEXT NOT NULL,
                    id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('data','logic','action','decision','preference')),
                    content TEXT NOT NULL,
                    source TEXT NOT NULL CHECK(source IN ('human','model','imported')),
                    author TEXT NOT NULL,
                    created TEXT NOT NULL,
                    imported INTEGER NOT NULL DEFAULT 0 CHECK(imported IN (0,1)),
                    search_text TEXT NOT NULL,
                    PRIMARY KEY(project, id)
                )
            """)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _public(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            **{field: row[field] for field in _FIELDS},
            "project": row["project"],
            "imported": bool(row["imported"]),
            "untrusted": True,
        }

    def _insert(self, connection: sqlite3.Connection, note: dict[str, Any], *, imported: bool) -> None:
        connection.execute(
            """INSERT INTO memory_notes
               (project,id,kind,content,source,author,created,imported,search_text)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                self.project, note["id"], note["kind"], note["content"],
                note["source"], note["author"], note["created"], int(imported),
                note["content"].casefold(),
            ),
        )

    def remember(
        self,
        kind: str,
        content: str,
        *,
        source: str = "human",
        author: str = "human",
        note_id: str | None = None,
        created: str | None = None,
    ) -> dict[str, Any]:
        """Append context; an existing ID cannot overwrite another author's note."""
        note = _record(kind, content, source, author, note_id, created)
        with self._connection() as connection:
            try:
                self._insert(connection, note, imported=False)
            except sqlite3.IntegrityError as error:
                raise ValueError("memory id already exists in this project") from error
        return self._public({**note, "project": self.project, "imported": False})

    def recall(
        self,
        query: str = "",
        *,
        kinds: Sequence[str] | None = None,
        limit: int = 20,
        char_budget: int = 6_000,
    ) -> list[dict[str, Any]]:
        """Retrieve newest matching context within a serialized JSON character budget.

        Search is literal, Unicode-casefolded and matches every whitespace
        separated query term. The JSON budget includes provenance and metadata
        using ``json.dumps(result, ensure_ascii=False)``. An oversized note is
        returned as a marked excerpt; the stored original remains unchanged.
        """
        if not isinstance(query, str) or len(query) > 512 or "\x00" in query:
            raise ValueError("memory query must be a string of at most 512 characters")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("memory limit must be an integer between 1 and 100")
        if type(char_budget) is not int or not 2 <= char_budget <= 65_536:
            raise ValueError("memory char_budget must be an integer between 2 and 65536")
        clauses, values = ["project = ?"], [self.project]
        if kinds is not None:
            if not isinstance(kinds, (list, tuple)) or any(
                not isinstance(kind, str) or kind not in MEMORY_KINDS for kind in kinds
            ):
                raise ValueError("memory kinds must be a list of supported memory kinds")
            if not kinds:
                return []
            clauses.append(f"kind IN ({','.join('?' for _ in kinds)})")
            values.extend(kinds)
        terms = query.casefold().split()
        if len(terms) > 32:
            raise ValueError("memory query must contain at most 32 terms")
        for term in terms:
            clauses.append("instr(search_text, ?) > 0")
            values.append(term)
        sql = f"SELECT * FROM memory_notes WHERE {' AND '.join(clauses)} ORDER BY rowid DESC LIMIT ?"
        with self._connection() as connection:
            rows = connection.execute(sql, [*values, limit]).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            note = self._public(row)
            if len(json.dumps([*results, note], ensure_ascii=False)) <= char_budget:
                results.append(note)
                continue
            original = note["content"]
            note.update(content="", truncated=True)
            if len(json.dumps([*results, note], ensure_ascii=False)) >= char_budget:
                continue
            low, high = 0, len(original)
            while low < high:
                middle = (low + high + 1) // 2
                note["content"] = original[:middle]
                if len(json.dumps([*results, note], ensure_ascii=False)) <= char_budget:
                    low = middle
                else:
                    high = middle - 1
            if low:
                note["content"] = original[:low]
                results.append(note)
        return results

    def forget(self, note_id: str) -> bool:
        """Remove a note from this project's future retrievals and exports."""
        _note_id(note_id)
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memory_notes WHERE project = ? AND id = ?", (self.project, note_id)
            )
            return cursor.rowcount == 1

    def export(self) -> dict[str, Any]:
        """Export portable notes, without inventing trust or approval metadata."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM memory_notes WHERE project = ? ORDER BY rowid", (self.project,)
            ).fetchall()
        return {
            "schema": MEMORY_SCHEMA,
            "project": self.project,
            "notes": [{field: row[field] for field in _FIELDS} for row in rows],
        }

    def import_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Atomically import declared provenance as untrusted context.

        Re-importing the same ID and contents is idempotent. Optional repository
        and exported_at metadata is accepted. Conflicts, unknown fields and
        scope mismatches reject the whole batch, without partial writes.
        Imports are bounded to 1000 notes and four million characters.
        """
        required = {"schema", "project", "notes"}
        allowed = required | {"repository", "exported_at"}
        if not isinstance(payload, dict) or not required <= set(payload) or not set(payload) <= allowed:
            raise ValueError("memory import has missing or unsupported top-level fields")
        if payload["schema"] != MEMORY_SCHEMA:
            raise ValueError(f"memory import schema must be {MEMORY_SCHEMA}")
        if payload["project"] != self.project:
            raise ValueError("memory import project does not match the active project")
        if "repository" in payload:
            _string(payload["repository"], "repository", 200)
        if "exported_at" in payload:
            _string(payload["exported_at"], "exported_at", 64)
            _created(payload["exported_at"])
        raw_notes = payload["notes"]
        if not isinstance(raw_notes, list) or len(raw_notes) > MAX_IMPORT_NOTES:
            raise ValueError(f"memory import notes must be a list of at most {MAX_IMPORT_NOTES} entries")
        notes = []
        total_chars = 0
        for raw in raw_notes:
            if not isinstance(raw, dict) or set(raw) != set(_FIELDS):
                raise ValueError(f"each imported memory note requires exactly {', '.join(_FIELDS)}")
            _note_id(raw["id"])
            _string(raw["created"], "created", 64)
            note = _record(raw["kind"], raw["content"], raw["source"], raw["author"], raw["id"], raw["created"])
            total_chars += len(json.dumps(note, ensure_ascii=False))
            if total_chars > MAX_IMPORT_CHARS:
                raise ValueError("memory import exceeds the character limit")
            notes.append(note)
        imported = []
        with self._connection() as connection:
            # Serialize the read/conflict/insert sequence across agent processes.
            connection.execute("BEGIN IMMEDIATE")
            for note in notes:
                existing = connection.execute(
                    "SELECT * FROM memory_notes WHERE project = ? AND id = ?", (self.project, note["id"])
                ).fetchone()
                if existing is not None:
                    if any(existing[field] != note[field] for field in _FIELDS):
                        raise ValueError(f"memory import id conflicts with an existing note: {note['id']}")
                    imported.append(self._public(existing))
                    continue
                self._insert(connection, note, imported=True)
                imported.append(self._public({**note, "project": self.project, "imported": True}))
        return imported
