from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlparse


PROTOCOL = "gptdoug-body-link-v1"
MAX_CLOCK_SKEW_SECONDS = 120


def canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_runtime_url(value: str) -> str:
    url = value.strip().rstrip("/")
    if not url:
        raise ValueError("GPT_DOUG_BODY_URL is required")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host == "replit.com" and "/@" in parsed.path:
        raise ValueError(
            "Replit workspace URLs are not runtime endpoints. Deploy the app and use its "
            "*.replit.app or custom-domain HTTPS URL."
        )

    local = host in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme not in ({"http", "https"} if local else {"https"}):
        raise ValueError("remote body URL must use HTTPS; HTTP is allowed only for localhost")
    if not host:
        raise ValueError("remote body URL must include a hostname")
    if parsed.query or parsed.fragment:
        raise ValueError("remote body URL must not include query or fragment components")
    return url


def _require_key(secret: str) -> bytes:
    raw = secret.encode("utf-8")
    if len(raw) < 32:
        raise ValueError("GPT_DOUG_BODY_LINK_KEY must be at least 32 bytes")
    return raw


def signature_message(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> bytes:
    return "\n".join(
        [
            PROTOCOL,
            method.upper(),
            path,
            timestamp,
            nonce,
            sha256_hex(body),
        ]
    ).encode("utf-8")


def sign(
    secret: str,
    *,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> str:
    key = _require_key(secret)
    message = signature_message(method, path, timestamp, nonce, body)
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify(
    secret: str,
    *,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
    signature: str,
    now: float | None = None,
    max_skew_seconds: int = MAX_CLOCK_SKEW_SECONDS,
) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = int(now if now is not None else time.time())
    if abs(current - ts) > max_skew_seconds:
        return False
    expected = sign(
        secret,
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )
    return hmac.compare_digest(expected, signature)
