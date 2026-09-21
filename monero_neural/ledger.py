from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class HashChainLedger:
    """Small append-only JSONL ledger with a SHA-256 hash chain.

    The ledger is not a blockchain and does not replace Monero consensus. It
    makes local neural-work provenance tamper-evident before optional Monero
    settlement references are attached.
    """

    GENESIS = "0" * 64

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o600)
        else:
            try:
                self.path.chmod(0o600)
            except OSError:
                pass

    def _rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not self.path.exists():
            return rows
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def rows(self, *, event: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self._rows()
        if event is None:
            return rows
        return [row for row in rows if row.get("event") == event]

    def head_hash(self) -> str:
        rows = self._rows()
        return rows[-1]["record_hash"] if rows else self.GENESIS

    def append(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        clean_event = " ".join(str(event).split()).strip()
        if not clean_event:
            raise ValueError("event must not be empty")
        with _LOCK:
            rows = self._rows()
            prev_hash = rows[-1]["record_hash"] if rows else self.GENESIS
            record: Dict[str, Any] = {
                "schema": "xunia/monero-neural-ledger-v1",
                "seq": len(rows) + 1,
                "event_id": "evt-" + uuid.uuid4().hex,
                "event": clean_event,
                "timestamp": utc_now(),
                "prev_hash": prev_hash,
                "payload": payload,
            }
            record["record_hash"] = hash_value(record)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return record

    def verify(self) -> Dict[str, Any]:
        rows = self._rows()
        expected_prev = self.GENESIS
        for index, row in enumerate(rows, start=1):
            if row.get("seq") != index:
                return {"valid": False, "reason": "sequence_mismatch", "seq": index}
            if row.get("prev_hash") != expected_prev:
                return {"valid": False, "reason": "previous_hash_mismatch", "seq": index}
            supplied = row.get("record_hash")
            body = dict(row)
            body.pop("record_hash", None)
            actual = hash_value(body)
            if supplied != actual:
                return {"valid": False, "reason": "record_hash_mismatch", "seq": index}
            expected_prev = str(supplied)
        return {"valid": True, "record_count": len(rows), "head_hash": expected_prev}
