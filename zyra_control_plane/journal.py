"""Tamper-evident JSONL mission event journal with local signing."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FAILURE_TYPES = {"planning", "tool", "validation", "review", "runtime"}
GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True)
class JournalHead:
    sequence: int
    digest: str


class MissionJournal:
    """Append-only hash-chained mission journal."""

    def __init__(self, path: str | Path, key_path: str | Path | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path = Path(key_path) if key_path else self.path.with_suffix(".key")
        self.key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            return self.key_path.read_bytes()
        key = secrets.token_bytes(32)
        self.key_path.write_bytes(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def _events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def head(self) -> JournalHead:
        events = self._events()
        if not events:
            return JournalHead(0, GENESIS)
        last = events[-1]
        return JournalHead(int(last["sequence"]), str(last["digest"]))

    def append(
        self,
        mission_id: str,
        event: str,
        *,
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        model_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        failure_type: str | None = None,
    ) -> dict[str, Any]:
        if failure_type is not None and failure_type not in FAILURE_TYPES:
            raise ValueError(f"unknown failure type: {failure_type}")
        head = self.head()
        base: dict[str, Any] = {
            "sequence": head.sequence + 1,
            "timestamp": time.time(),
            "mission_id": mission_id,
            "event": event,
            "data": data or {},
            "telemetry": {
                "duration_ms": duration_ms,
                "model_calls": int(model_calls),
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
            },
            "failure_type": failure_type,
            "previous_digest": head.digest,
        }
        digest = hashlib.sha256(_canonical(base)).hexdigest()
        signature = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
        record = {**base, "digest": digest, "signature": signature}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def verify(self) -> dict[str, Any]:
        previous = GENESIS
        count = 0
        for expected_sequence, record in enumerate(self._events(), start=1):
            base = {key: value for key, value in record.items() if key not in {"digest", "signature"}}
            digest = hashlib.sha256(_canonical(base)).hexdigest()
            signature = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
            valid = (
                int(record.get("sequence", -1)) == expected_sequence
                and record.get("previous_digest") == previous
                and hmac.compare_digest(str(record.get("digest", "")), digest)
                and hmac.compare_digest(str(record.get("signature", "")), signature)
            )
            if not valid:
                return {"ok": False, "events": count, "failed_sequence": expected_sequence, "head": previous}
            previous = digest
            count += 1
        return {"ok": True, "events": count, "head": previous}

    def mission_events(self, mission_id: str) -> list[dict[str, Any]]:
        return [event for event in self._events() if event.get("mission_id") == mission_id]

    def policy_snapshot(self, mission_id: str, policy: dict[str, Any]) -> dict[str, Any]:
        return self.append(mission_id, "POLICY_SNAPSHOT", data={"policy": policy})
