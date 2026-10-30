"""GPT-Delta provenance ledger with optional S-Brain bridge.

The standalone SQLite backend works on the current main branch. If S-Brain is
installed, use its canonical memory store instead. Neither backend validates
whether an external source's claims are true.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ai_killswitch import require_ai_allowed

_SECRET = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"api[_-]?key\s*[:=]\s*\S{12,}|password\s*[:=]\s*\S{8,}|"
    r"bearer\s+[A-Za-z0-9._~+/-]{16,})", re.IGNORECASE,
)


def _clean_fields(*, subject: str, predicate: str, value: str,
                  source_id: str, source_uri: str, observed_at: Optional[str],
                  confidence: float) -> dict[str, Any]:
    values = {k: v.strip() if isinstance(v, str) else "" for k, v in (
        ("subject", subject), ("predicate", predicate), ("value", value),
        ("source_id", source_id), ("source_uri", source_uri),
    )}
    if any(not text or len(text) > 2400 for text in values.values()):
        raise ValueError("all evidence fields must be strings of 1..2400 characters")
    if any(_SECRET.search(text) for text in values.values()):
        raise ValueError("secret-like material must not be stored in evidence")
    if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be a finite number between zero and one")
    if observed_at is None:
        observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("observed_at must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must have a timezone")
    values["observed_at"] = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    values["confidence"] = float(confidence)
    return values


def _observe_standalone(database: str | Path, clean: dict[str, Any]) -> dict[str, Any]:
    filename = Path(database)
    if filename.is_symlink() or filename.parent.is_symlink():
        raise ValueError("refusing symlinked evidence storage")
    filename.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(filename), timeout=10)
    try:
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("""CREATE TABLE IF NOT EXISTS gpt_delta_evidence (
            evidence_id TEXT PRIMARY KEY, subject TEXT NOT NULL, predicate TEXT NOT NULL,
            value TEXT NOT NULL, source_id TEXT NOT NULL, source_uri TEXT NOT NULL,
            observed_at TEXT NOT NULL, confidence REAL NOT NULL
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS delta_evidence_topic ON gpt_delta_evidence(subject,predicate)")
        existing = con.execute(
            "SELECT value,source_id,source_uri FROM gpt_delta_evidence "
            "WHERE lower(subject)=lower(?) AND lower(predicate)=lower(?) LIMIT 10000",
            (clean["subject"], clean["predicate"]),
        ).fetchall()
        if any(old_value == clean["value"] and old_id == clean["source_id"]
               and old_uri == clean["source_uri"] for old_value, old_id, old_uri in existing):
            return {"event": "duplicate", "material": False,
                    "subject": clean["subject"], "predicate": clean["predicate"],
                    "stored": False, "independently_verified": False}
        contradicts = any(row[0] != clean["value"] for row in existing)
        event = "new" if not existing else ("changed" if contradicts else "corroborated")
        canonical = {k: clean[k] for k in (
            "subject", "predicate", "value", "source_id", "source_uri", "observed_at",
        )}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True,
                                          ensure_ascii=False).encode()).hexdigest()
        with con:
            cursor = con.execute("INSERT OR IGNORE INTO gpt_delta_evidence VALUES (?,?,?,?,?,?,?,?)", (
                digest, clean["subject"], clean["predicate"], clean["value"],
                clean["source_id"], clean["source_uri"], clean["observed_at"], clean["confidence"],
            ))
        return {
            "event": event, "material": event in {"new", "changed"},
            "subject": clean["subject"], "predicate": clean["predicate"],
            "evidence_id": digest, "source_id": clean["source_id"],
            "stored": cursor.rowcount == 1, "contradictory_values": contradicts,
            "previous_source_ids": sorted({row[1] for row in existing}),
            "backend": "standalone-sqlite", "independently_verified": False,
        }
    finally:
        con.close()


def observe_change(
    *, database: str | Path, subject: str, predicate: str, value: str,
    source_id: str, source_uri: str, observed_at: Optional[str] = None,
    confidence: float = 0.5,
) -> dict[str, Any]:
    require_ai_allowed("GPT-Delta evidence intake")
    clean = _clean_fields(subject=subject, predicate=predicate, value=value,
                          source_id=source_id, source_uri=source_uri,
                          observed_at=observed_at, confidence=confidence)
    try:
        from gpt_brain.s_brain import Evidence, SBrain
    except ModuleNotFoundError as exc:
        if exc.name != "gpt_brain.s_brain":
            raise
        return _observe_standalone(database, clean)
    # In environments with S-Brain, use its shared durable ontology store.
    fact = Evidence(**clean)
    with SBrain(database) as brain:
        old = [row for row in brain._all_records()
               if row["subject"].casefold() == clean["subject"].casefold()
               and row["predicate"].casefold() == clean["predicate"].casefold()]
        if any(row["value"] == clean["value"] and row["source_id"] == clean["source_id"]
               and row["source_uri"] == clean["source_uri"] for row in old):
            return {"event": "duplicate", "material": False,
                    "subject": clean["subject"], "predicate": clean["predicate"],
                    "stored": False, "independently_verified": False}
        contradicts = bool(old and any(row["value"] != clean["value"] for row in old))
        event = "new" if not old else ("changed" if contradicts else "corroborated")
        stored = brain.remember(fact)
        return {
            "event": event, "material": event in {"new", "changed"},
            "subject": clean["subject"], "predicate": clean["predicate"],
            "evidence_id": stored["id"], "source_id": clean["source_id"],
            "stored": stored["inserted"], "contradictory_values": contradicts,
            "previous_source_ids": sorted({row["source_id"] for row in old}),
            "backend": "s-brain", "independently_verified": False,
        }
