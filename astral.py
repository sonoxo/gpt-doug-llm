"""ASTRAL high-assurance elevation controls for EUREKA 369."""

from __future__ import annotations

import base64
import os
import re
import time
import hashlib
import hmac
import json
from pathlib import Path
from dataclasses import dataclass

from auth_gate import ThreeFactorGate, VerifiedIdentity


@dataclass(frozen=True)
class AstralConfig:
    security_officer: VerifiedIdentity
    audit_hmac_key: bytes
    session_seconds: int = 300
    max_commands: int = 20
    max_failures: int = 5
    lockout_seconds: int = 900

    @classmethod
    def from_environment(cls, primary: VerifiedIdentity) -> "AstralConfig":
        email = os.getenv("ASTRAL_SECURITY_OFFICER_EMAIL", "").strip().lower()
        phone = os.getenv("ASTRAL_SECURITY_OFFICER_PHONE", "").strip()
        secret = os.getenv("ASTRAL_SECURITY_OFFICER_TOTP_SECRET", "").strip().replace(" ", "").upper()
        raw_key = os.getenv("ASTRAL_AUDIT_HMAC_KEY", "").strip()
        if not all((email, phone, secret, raw_key)):
            raise ValueError("ASTRAL requires a security officer identity and audit HMAC key")
        if email == primary.business_email or phone == primary.telephone:
            raise ValueError("ASTRAL security officer must be independent from the requesting developer")
        if not re.fullmatch(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", email, re.I):
            raise ValueError("invalid ASTRAL security officer email")
        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
            raise ValueError("invalid ASTRAL security officer phone")
        officer = VerifiedIdentity(email, phone, secret)
        try:
            base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
        except Exception as error:
            raise ValueError("invalid ASTRAL security officer authenticator secret") from error
        try:
            audit_key = base64.b64decode(raw_key, validate=True)
        except Exception as error:
            raise ValueError("ASTRAL audit key must be valid base64") from error
        if len(audit_key) < 32:
            raise ValueError("ASTRAL audit key must contain at least 256 bits")
        return cls(officer, audit_key)


class AstralGate:
    """Two-person authorization with bounded sessions and lockout."""

    def __init__(self, config: AstralConfig, primary_gate: ThreeFactorGate, state_path: str | Path | None = None):
        self.config = config
        self.primary_gate = primary_gate
        self.officer_gate = ThreeFactorGate(config.security_officer)
        self.state_path = Path(state_path or Path.home() / ".gpt-doug" / "astral-lockout.json")
        self.failures, self.locked_until = self._load_state()

    def authorize(self, developer_code: str, officer_code: str, now: float | None = None) -> bool:
        moment = now if now is not None else time.time()
        if moment < self.locked_until:
            return False
        allowed = self.primary_gate.authenticate(developer_code) and self.officer_gate.authenticate(officer_code)
        if allowed:
            self.failures = 0
            self.locked_until = 0.0
            self._save_state()
            return True
        self.failures += 1
        if self.failures >= self.config.max_failures:
            self.locked_until = moment + self.config.lockout_seconds
        self._save_state()
        return False

    def _signature(self, payload: dict) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return hmac.new(self.config.audit_hmac_key, raw, hashlib.sha256).hexdigest()

    def _load_state(self) -> tuple[int, float]:
        if not self.state_path.exists():
            return 0, 0.0
        try:
            record = json.loads(self.state_path.read_text(encoding="utf-8"))
            signature = record.pop("hmac_sha256")
            if not hmac.compare_digest(signature, self._signature(record)):
                raise ValueError("signature mismatch")
            return int(record["failures"]), float(record["locked_until"])
        except Exception as error:
            raise ValueError("ASTRAL lockout state integrity failure") from error

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = {"failures": self.failures, "locked_until": self.locked_until}
        record = {**payload, "hmac_sha256": self._signature(payload)}
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(self.state_path)
