"""Per-person accounts for the ideas marketplace.

Distinct from auth.py's single shared operator password (the outer gate
that stops the public tunnel being wide open). This layer sits inside
that gate and gives individual people using the app their own identity,
so ideas/runs can be attributed to a person instead of the single
"operator" placeholder.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(DIR, "users.json")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{2,20}$")
PBKDF2_ITERATIONS = 200_000
SESSION_TTL = 60 * 60 * 24 * 30  # 30 days

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 8

_lock = threading.RLock()
_data = None
_rate_hits: dict[str, list] = {}


def _load():
    global _data
    if _data is not None:
        return _data
    if os.path.isfile(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                _data = json.load(f)
                return _data
        except (OSError, json.JSONDecodeError):
            pass
    _data = {"users": {}, "sessions": {}}
    return _data


def _save():
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_data, f, indent=2)
    os.replace(tmp, USERS_FILE)


def _hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return salt, digest.hex()


def rate_limited(ip):
    now = time.time()
    with _lock:
        hits = [t for t in _rate_hits.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
        hits.append(now)
        _rate_hits[ip] = hits
        return len(hits) > RATE_LIMIT_MAX


def signup(username, password):
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise ValueError("invalid username (2-20 letters/numbers/_)")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    with _lock:
        data = _load()
        if username in data["users"]:
            raise ValueError("username already taken")
        salt, digest = _hash(password)
        data["users"][username] = {"salt": salt, "password_hash": digest, "created": time.time()}
        _save()
        return _issue_session(username)


def login(username, password):
    username = username.strip().lower()
    with _lock:
        data = _load()
        user = data["users"].get(username)
        if not user or not hmac.compare_digest(_hash(password, user["salt"])[1], user["password_hash"]):
            raise ValueError("invalid username or password")
        return _issue_session(username)


def _issue_session(username):
    with _lock:
        data = _load()
        token = secrets.token_hex(32)
        data["sessions"][token] = {"username": username, "expires_at": time.time() + SESSION_TTL}
        _save()
        return token


def current_user(token):
    if not token:
        return None
    with _lock:
        data = _load()
        session = data["sessions"].get(token)
        if not session:
            return None
        if session["expires_at"] < time.time():
            del data["sessions"][token]
            _save()
            return None
        return session["username"]
