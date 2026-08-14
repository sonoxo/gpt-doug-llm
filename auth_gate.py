"""Three-factor access gate for GPT Doug's local terminal client."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import struct
import time
from dataclasses import dataclass


FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "aol.com", "proton.me", "protonmail.com", "mail.com",
}


@dataclass(frozen=True)
class VerifiedIdentity:
    business_email: str
    telephone: str
    totp_secret: str

    @classmethod
    def from_environment(cls) -> "VerifiedIdentity":
        email = os.getenv("GPT_DOUG_VERIFIED_BUSINESS_EMAIL", "").strip().lower()
        phone = os.getenv("GPT_DOUG_VERIFIED_PHONE", "").strip()
        secret = os.getenv("GPT_DOUG_TOTP_SECRET", "").strip().replace(" ", "").upper()
        if not email or not phone or not secret:
            raise ValueError("verified business email, phone, and TOTP secret are required")
        if not re.fullmatch(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", email, re.I):
            raise ValueError("invalid business email")
        domain = email.rsplit("@", 1)[1]
        allowed = {d.strip().lower() for d in os.getenv("GPT_DOUG_ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()}
        if domain in FREE_EMAIL_DOMAINS or (allowed and domain not in allowed):
            raise ValueError("email domain is not an approved business domain")
        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
            raise ValueError("telephone must use E.164 format")
        try:
            base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
        except Exception as error:
            raise ValueError("invalid Google Authenticator secret") from error
        return cls(email, phone, secret)


def totp(secret: str, at_time: int | None = None) -> str:
    moment = int(at_time if at_time is not None else time.time())
    counter = struct.pack(">Q", moment // 30)
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{number:06d}"


class ThreeFactorGate:
    def __init__(self, identity: VerifiedIdentity):
        self.identity = identity

    def verify_totp(self, code: str, at_time: int | None = None) -> bool:
        now = int(at_time if at_time is not None else time.time())
        return any(hmac.compare_digest(code, totp(self.identity.totp_secret, now + drift * 30)) for drift in (-1, 0, 1))

    def authenticate(self, code: str) -> bool:
        return bool(re.fullmatch(r"\d{6}", code)) and self.verify_totp(code)

    def summary(self) -> str:
        domain = self.identity.business_email.rsplit("@", 1)[1]
        return f"business_domain={domain} // phone=***{self.identity.telephone[-4:]} // google_auth=verified"
