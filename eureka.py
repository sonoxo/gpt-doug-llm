"""EUREKA: a small, auditable protocol for cooperative AI messages."""

from __future__ import annotations

import json
import uuid
import hashlib
import hmac
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
    signature: str = ""

    @classmethod
    def create(cls, signal: Signal, sender: str, recipient: str, purpose: str, payload: dict, authorized_by: str, signing_key: bytes) -> "EurekaMessage":
        fields = (sender, recipient, purpose, authorized_by)
        if any(not value or len(value) > 256 for value in fields):
            raise ValueError("EUREKA identity, purpose, and authorization fields are required")
        encoded = json.dumps(payload)
        if len(encoded.encode()) > 32_768:
            raise ValueError("EUREKA payload exceeds 32 KiB")
        if len(signing_key) < 32:
            raise ValueError("EUREKA signing key must contain at least 256 bits")
        message = cls(signal, sender, recipient, purpose, payload, authorized_by, str(uuid.uuid4()), datetime.now(timezone.utc).isoformat())
        unsigned = message._unsigned_json().encode()
        return cls(**{**asdict(message), "signal": signal, "signature": hmac.new(signing_key, unsigned, hashlib.sha256).hexdigest()})

    def _unsigned_json(self) -> str:
        data = asdict(self); data["signal"] = self.signal.value; data.pop("signature", None)
        return json.dumps(data, separators=(",", ":"), sort_keys=True)

    def to_json(self) -> str:
        data = asdict(self)
        data["signal"] = self.signal.value
        return json.dumps(data, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str, signing_key: bytes, seen_ids: set[str] | None = None) -> "EurekaMessage":
        data = json.loads(raw)
        if data.pop("protocol", None) != "EUREKA/1.0":
            raise ValueError("unsupported EUREKA protocol")
        required = {"signal", "sender", "recipient", "purpose", "payload", "authorized_by", "message_id", "timestamp", "signature"}
        if set(data) != required or not isinstance(data["payload"], dict):
            raise ValueError("invalid EUREKA message schema")
        data["signal"] = Signal(data["signal"])
        message = cls(protocol="EUREKA/1.0", **data)
        expected = hmac.new(signing_key, message._unsigned_json().encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(message.signature, expected):
            raise ValueError("invalid EUREKA signature")
        if seen_ids is not None:
            if message.message_id in seen_ids: raise ValueError("replayed EUREKA message")
            seen_ids.add(message.message_id)
        return message
