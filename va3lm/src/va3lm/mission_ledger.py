from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissionLedger:
    """Durable, append-audited mission history for the Black House control plane."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("BLACK_HOUSE_LEDGER_PATH")
        self.path = Path(configured or ".black-house/mission-history.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    target TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    approval_state TEXT NOT NULL,
                    envelope_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mission_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES missions(mission_id)
                );
                CREATE INDEX IF NOT EXISTS idx_mission_events_mission
                ON mission_events(mission_id, id);
                """
            )

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    def create(self, envelope: dict[str, Any], *, status: str = "RECEIVED") -> dict[str, Any]:
        now = _utc_now()
        mission_id = str(envelope["missionId"])
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO missions (
                    mission_id, created_at, updated_at, status, requested_by, intent,
                    target, classification, approval_state, envelope_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    requested_by=excluded.requested_by,
                    intent=excluded.intent,
                    target=excluded.target,
                    classification=excluded.classification,
                    approval_state=excluded.approval_state,
                    envelope_json=excluded.envelope_json
                """,
                (
                    mission_id,
                    now,
                    now,
                    status,
                    envelope["requestedBy"],
                    envelope["intent"],
                    envelope["target"],
                    envelope["classification"],
                    envelope["approvalState"],
                    self._serialize(envelope),
                ),
            )
        self.append_event(mission_id, "MISSION_RECEIVED", "RVIA", {"status": status})
        return self.get(mission_id)

    def update(
        self,
        mission_id: str,
        envelope: dict[str, Any],
        *,
        status: str,
        event_type: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE missions SET
                    updated_at=?, status=?, approval_state=?, envelope_json=?
                WHERE mission_id=?
                """,
                (
                    now,
                    status,
                    envelope["approvalState"],
                    self._serialize(envelope),
                    mission_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown mission: {mission_id}")
        self.append_event(mission_id, event_type, actor, details or {"status": status})
        return self.get(mission_id)

    def append_event(
        self,
        mission_id: str,
        event_type: str,
        actor: str,
        details: dict[str, Any],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mission_events (
                    mission_id, observed_at, event_type, actor, details_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (mission_id, _utc_now(), event_type, actor, self._serialize(details)),
            )

    def get(self, mission_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        return self._mission_row(row)

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        bounded = min(max(limit, 1), 500)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM missions ORDER BY updated_at DESC LIMIT ?", (bounded,)
            ).fetchall()
        return [self._mission_row(row) for row in rows]

    def timeline(self, mission_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT observed_at, event_type, actor, details_json
                FROM mission_events WHERE mission_id=? ORDER BY id ASC
                """,
                (mission_id,),
            ).fetchall()
        return [
            {
                "observedAt": row["observed_at"],
                "eventType": row["event_type"],
                "actor": row["actor"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]

    def summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
            rows = connection.execute(
                "SELECT status, COUNT(*) AS total FROM missions GROUP BY status"
            ).fetchall()
        return {
            "ledger": str(self.path),
            "missions": total,
            "byStatus": {row["status"]: row["total"] for row in rows},
        }

    @staticmethod
    def _mission_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "missionId": row["mission_id"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "status": row["status"],
            "requestedBy": row["requested_by"],
            "intent": row["intent"],
            "target": row["target"],
            "classification": row["classification"],
            "approvalState": row["approval_state"],
            "envelope": json.loads(row["envelope_json"]),
        }
