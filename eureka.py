"""EUREKA: a small, auditable protocol for cooperative AI messages."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum


class Signal(str, Enum):
    HELLO = "HELLO"
    PLAN = "PLAN"
    REQUEST = "REQUEST"
    EVIDENCE = "EVIDENCE"
    DECISION = "DECISION"
    HANDOFF = "HANDOFF"


@dataclass(frozen=True)
class EurekaMessage:
    signal: Signal
    sender: str
    recipient: str
    purpose: str
    payload: dict
    authorized_by: str
    message_id: str
    timestamp: str
    protocol: str = "EUREKA/1.0"

    @classmethod
    def create(cls, signal: Signal, sender: str, recipient: str, purpose: str, payload: dict, authorized_by: str) -> "EurekaMessage":
        fields = (sender, recipient, purpose, authorized_by)
        if any(not value or len(value) > 256 for value in fields):
            raise ValueError("EUREKA identity, purpose, and authorization fields are required")
        encoded = json.dumps(payload)
        if len(encoded.encode()) > 32_768:
            raise ValueError("EUREKA payload exceeds 32 KiB")
        return cls(signal, sender, recipient, purpose, payload, authorized_by, str(uuid.uuid4()), datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        data = asdict(self)
        data["signal"] = self.signal.value
        return json.dumps(data, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "EurekaMessage":
        data = json.loads(raw)
        if data.pop("protocol", None) != "EUREKA/1.0":
            raise ValueError("unsupported EUREKA protocol")
        required = {"signal", "sender", "recipient", "purpose", "payload", "authorized_by", "message_id", "timestamp"}
        if set(data) != required or not isinstance(data["payload"], dict):
            raise ValueError("invalid EUREKA message schema")
        data["signal"] = Signal(data["signal"])
        return cls(protocol="EUREKA/1.0", **data)
