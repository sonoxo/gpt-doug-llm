"""Single-password gate for gpt-doug-web.

This app has no per-user accounts — it's one operator's local tool. This
module exists only to stop it being wide open to anyone who finds the
public URL once it's tunneled/deployed. If DOUG_ACCESS_PASSWORD isn't set,
a random one is generated at startup and printed to the console/log so the
operator can still log in, rather than silently running unauthenticated.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

SESSION_TTL = 60 * 60 * 24 * 7  # 7 days
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 8

_lock = threading.Lock()
_sessions: dict[str, float] = {}  # token -> expires_at
_rate_hits: dict[str, list] = {}  # ip -> [timestamps]

_password = os.environ.get("DOUG_ACCESS_PASSWORD")
_generated = False
if not _password:
    _password = secrets.token_urlsafe(12)
    _generated = True


def startup_message():
    if _generated:
        return (
            "No DOUG_ACCESS_PASSWORD set — generated one for this run:\n"
            f"    {_password}\n"
            "Set DOUG_ACCESS_PASSWORD to pin a permanent password instead."
        )
    return "Using DOUG_ACCESS_PASSWORD from environment."


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def check_password(candidate):
    return hmac.compare_digest(_sha(candidate), _sha(_password))


def rate_limited(ip):
    now = time.time()
    with _lock:
        hits = [t for t in _rate_hits.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
        hits.append(now)
        _rate_hits[ip] = hits
        return len(hits) > RATE_LIMIT_MAX


def create_session():
    token = secrets.token_hex(32)
    with _lock:
        _sessions[token] = time.time() + SESSION_TTL
    return token


def valid_session(token):
    if not token:
        return False
    with _lock:
        expires = _sessions.get(token)
        if expires is None:
            return False
        if expires < time.time():
            del _sessions[token]
            return False
        return True


def parse_cookie(header, name):
    if not header:
        return None
    for part in header.split(";"):
        part = part.strip()
        if part.startswith(name + "="):
            return part[len(name) + 1:]
    return None
