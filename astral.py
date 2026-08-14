"""ASTRAL high-assurance elevation controls for EUREKA 369."""

from __future__ import annotations

import base64
import os
import re
import time
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

    def __init__(self, config: AstralConfig, primary_gate: ThreeFactorGate):
        self.config = config
        self.primary_gate = primary_gate
        self.officer_gate = ThreeFactorGate(config.security_officer)
        self.failures = 0
        self.locked_until = 0.0

    def authorize(self, developer_code: str, officer_code: str, now: float | None = None) -> bool:
        moment = now if now is not None else time.time()
        if moment < self.locked_until:
            return False
        allowed = self.primary_gate.authenticate(developer_code) and self.officer_gate.authenticate(officer_code)
        if allowed:
            self.failures = 0
            return True
        self.failures += 1
        if self.failures >= self.config.max_failures:
            self.locked_until = moment + self.config.lockout_seconds
        return False
