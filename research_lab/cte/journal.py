"""Durable execution journal for ZYRA-CTE."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional

PHASES = frozenset(
    {
        "PROPOSED",
        "SIMULATED",
        "AUTHORIZED",
        "EXECUTING",
        "OBSERVED",
        "COMMITTED",
        "ROLLED_BACK",
    }
)

TERMINAL_PHASES = frozenset({"COMMITTED", "ROLLED_BACK"})

LEGAL_TRANSITIONS = {
    "PROPOSED": frozenset({"SIMULATED"}),
    "SIMULATED": frozenset({"AUTHORIZED", "ROLLED_BACK"}),
    "AUTHORIZED": frozenset({"EXECUTING", "ROLLED_BACK"}),
    "EXECUTING": frozenset({"OBSERVED", "ROLLED_BACK"}),
    "OBSERVED": frozenset({"COMMITTED", "ROLLED_BACK"}),
    "COMMITTED": frozenset(),
    "ROLLED_BACK": frozenset(),
}


@dataclass(frozen=True)
class JournalAttempt:
    attempt_id: str
    transition_id: str
    base_version: str
    phase: str
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    attempt_id: str
    from_phase: Optional[str]
    to_phase: str
    at: int
    payload: Dict[str, Any]


class ExecutionJournal:
    """SQLite-backed CTE lifecycle journal.

    The journal records synthetic execution state only. It does not perform
    external mutations.
    """

    def __init__(self, database):
        self.db = sqlite3.connect(database)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")

        with self.db:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cte_journal_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    transition_id TEXT NOT NULL,
                    base_version TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cte_journal_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL,
                    from_phase TEXT,
                    to_phase TEXT NOT NULL,
                    at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (attempt_id)
                        REFERENCES cte_journal_attempts(attempt_id)
                )
                """
            )
            self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    cte_journal_events_attempt_idx
                ON cte_journal_events(attempt_id, sequence)
                """
            )

    def close(self):
        self.db.close()

    @staticmethod
    def _attempt(row):
        return JournalAttempt(
            attempt_id=row["attempt_id"],
            transition_id=row["transition_id"],
            base_version=row["base_version"],
            phase=row["phase"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row(self, attempt_id):
        return self.db.execute(
            """
            SELECT
                attempt_id,
                transition_id,
                base_version,
                phase,
                created_at,
                updated_at
            FROM cte_journal_attempts
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchone()

    def get(self, attempt_id):
        row = self._row(attempt_id)
        return None if row is None else self._attempt(row)

    def start(
        self,
        attempt_id,
        transition_id,
        base_version,
        now,
        request_binding=None,
    ):
        """Create an attempt or replay the identical idempotent request."""

        if not str(attempt_id).strip():
            raise ValueError("attempt_id is required")
        if not str(transition_id).strip():
            raise ValueError("transition_id is required")
        if not str(base_version).strip():
            raise ValueError("base_version is required")

        now = int(now)

        with self.db:
            cursor = self.db.execute(
                """
                INSERT OR IGNORE INTO cte_journal_attempts (
                    attempt_id,
                    transition_id,
                    base_version,
                    phase,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'PROPOSED', ?, ?)
                """,
                (
                    attempt_id,
                    transition_id,
                    base_version,
                    now,
                    now,
                ),
            )

            created = cursor.rowcount == 1
            row = self._row(attempt_id)

            if (
                row["transition_id"] != transition_id
                or row["base_version"] != base_version
            ):
                raise ValueError(
                    "attempt_id already bound to a different transaction"
                )

            if created:
                payload = {}
                if request_binding is not None:
                    payload["request_binding"] = str(request_binding)

                self.db.execute(
                    """
                    INSERT INTO cte_journal_events (
                        attempt_id,
                        from_phase,
                        to_phase,
                        at,
                        payload_json
                    )
                    VALUES (?, NULL, 'PROPOSED', ?, ?)
                    """,
                    (
                        attempt_id,
                        now,
                        json.dumps(
                            payload,
                            allow_nan=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                    ),
                )

            elif request_binding is not None:
                event = self.db.execute(
                    """
                    SELECT payload_json
                    FROM cte_journal_events
                    WHERE attempt_id = ?
                    ORDER BY sequence
                    LIMIT 1
                    """,
                    (attempt_id,),
                ).fetchone()

                existing = (
                    json.loads(event["payload_json"])
                    .get("request_binding")
                )

                if existing != str(request_binding):
                    raise ValueError(
                        "attempt_id already bound to a different request"
                    )

        return self.get(attempt_id)

    def advance(
        self,
        attempt_id,
        to_phase,
        now,
        payload=None,
    ):
        """Advance through a legal lifecycle transition.

        Repeating the already-current phase is an idempotent no-op.
        """

        if to_phase not in PHASES:
            raise ValueError("unknown CTE journal phase")

        now = int(now)
        payload_json = json.dumps(
            {} if payload is None else payload,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )

        with self.db:
            row = self._row(attempt_id)

            if row is None:
                raise KeyError("unknown execution attempt")

            current = row["phase"]

            if current == to_phase:
                return self._attempt(row)

            if current in TERMINAL_PHASES:
                raise ValueError("terminal execution attempt is immutable")

            if to_phase not in LEGAL_TRANSITIONS[current]:
                raise ValueError(
                    "illegal CTE journal transition: "
                    f"{current} -> {to_phase}"
                )

            if now < row["updated_at"]:
                raise ValueError("journal time cannot move backwards")

            cursor = self.db.execute(
                """
                UPDATE cte_journal_attempts
                SET phase = ?, updated_at = ?
                WHERE attempt_id = ? AND phase = ?
                """,
                (
                    to_phase,
                    now,
                    attempt_id,
                    current,
                ),
            )

            if cursor.rowcount != 1:
                latest = self._row(attempt_id)
                if latest is not None and latest["phase"] == to_phase:
                    return self._attempt(latest)
                raise RuntimeError("concurrent journal transition detected")

            self.db.execute(
                """
                INSERT INTO cte_journal_events (
                    attempt_id,
                    from_phase,
                    to_phase,
                    at,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    current,
                    to_phase,
                    now,
                    payload_json,
                ),
            )

        return self.get(attempt_id)

    def events(self, attempt_id):
        rows = self.db.execute(
            """
            SELECT
                sequence,
                attempt_id,
                from_phase,
                to_phase,
                at,
                payload_json
            FROM cte_journal_events
            WHERE attempt_id = ?
            ORDER BY sequence
            """,
            (attempt_id,),
        ).fetchall()

        return [
            JournalEvent(
                sequence=row["sequence"],
                attempt_id=row["attempt_id"],
                from_phase=row["from_phase"],
                to_phase=row["to_phase"],
                at=row["at"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def recoverable(self):
        """Return non-terminal attempts after process restart."""

        rows = self.db.execute(
            """
            SELECT
                attempt_id,
                transition_id,
                base_version,
                phase,
                created_at,
                updated_at
            FROM cte_journal_attempts
            WHERE phase NOT IN ('COMMITTED', 'ROLLED_BACK')
            ORDER BY created_at, attempt_id
            """
        ).fetchall()

        return [self._attempt(row) for row in rows]
