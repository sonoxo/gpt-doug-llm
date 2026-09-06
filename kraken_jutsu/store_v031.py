from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .models_v031 import Appointment

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS objects(
  object_id TEXT PRIMARY KEY,
  object_type TEXT NOT NULL,
  data_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS links(
  src_id TEXT NOT NULL,
  link_type TEXT NOT NULL,
  dst_id TEXT NOT NULL,
  data_json TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL,
  PRIMARY KEY(src_id, link_type, dst_id)
);
CREATE TABLE IF NOT EXISTS appointments(
  appointment_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  confidence REAL NOT NULL,
  score REAL NOT NULL,
  reasons_json TEXT NOT NULL,
  permissions_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


class OntologyStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert_object(self, object_id: str, object_type: str, data: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO objects(object_id,object_type,data_json,updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(object_id) DO UPDATE SET
                 object_type=excluded.object_type,
                 data_json=excluded.data_json,
                 updated_at=excluded.updated_at""",
            (object_id, object_type, json.dumps(data, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def get_object(self, object_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM objects WHERE object_id=?", (object_id,)).fetchone()
        if not row:
            return None
        return {
            "object_id": row["object_id"],
            "object_type": row["object_type"],
            "data": json.loads(row["data_json"]),
            "updated_at": row["updated_at"],
        }

    def list_objects(self, object_type: str | None = None) -> list[dict[str, Any]]:
        if object_type:
            rows = self.conn.execute(
                "SELECT * FROM objects WHERE object_type=? ORDER BY updated_at DESC",
                (object_type,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM objects ORDER BY updated_at DESC").fetchall()
        return [
            {
                "object_id": r["object_id"],
                "object_type": r["object_type"],
                "data": json.loads(r["data_json"]),
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def link(self, src_id: str, link_type: str, dst_id: str, data: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO links(src_id,link_type,dst_id,data_json,created_at) VALUES(?,?,?,?,?)",
            (src_id, link_type, dst_id, json.dumps(data or {}, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def add_appointment(self, appointment: Appointment) -> None:
        a = appointment.to_dict()
        self.conn.execute(
            "INSERT OR REPLACE INTO appointments VALUES(?,?,?,?,?,?,?,?)",
            (
                a["appointment_id"], a["agent_id"], a["role"], a["confidence"],
                a["score"], json.dumps(a["reasons"]),
                json.dumps(a["recommended_permissions"]), a["created_at"],
            ),
        )
        self.conn.commit()

    def latest_appointment(self, agent_id: str) -> dict[str, Any] | None:
        r = self.conn.execute(
            "SELECT * FROM appointments WHERE agent_id=? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if not r:
            return None
        return {
            "appointment_id": r["appointment_id"],
            "agent_id": r["agent_id"],
            "role": r["role"],
            "confidence": r["confidence"],
            "score": r["score"],
            "reasons": json.loads(r["reasons_json"]),
            "recommended_permissions": json.loads(r["permissions_json"]),
            "created_at": r["created_at"],
        }
