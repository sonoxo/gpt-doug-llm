"""Evidence-bound, single-use local admission receipts.

The host authenticates approvers and supplies trusted snapshots. This module does
not establish human identity or execute actions. SQLite is the local trust store.
"""
import hashlib
import json
import math
import secrets
import sqlite3


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {"mission", "action", "code", "data", "policy"}:
        raise ValueError("snapshot requires mission/action/code/data/policy")
    for key in ("mission", "action"):
        if not isinstance(snapshot[key], str) or not snapshot[key].strip():
            raise ValueError("mission/action must be nonempty strings")
    for key in ("code", "data", "policy"):
        if not isinstance(snapshot[key], dict) or not snapshot[key]:
            raise ValueError("nonempty version maps required")
        for name, version in snapshot[key].items():
            if not isinstance(name, str) or not name or not isinstance(version, str) or len(version) != 64:
                raise ValueError("resource names and SHA-256 digests required")
            if any(c not in "0123456789abcdef" for c in version):
                raise ValueError("invalid SHA-256 digest")
    return digest(snapshot)


class ApprovalGate:
    def __init__(self, database, approvers):
        self.approvers = frozenset(approvers)
        self.db = sqlite3.connect(database, timeout=10)
        self.db.execute("CREATE TABLE IF NOT EXISTS approvals (token_hash TEXT PRIMARY KEY, binding TEXT NOT NULL, approver TEXT NOT NULL, issued REAL NOT NULL, expires REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)")
        self.db.commit()

    def close(self):
        self.db.close()

    def issue(self, snapshot, authenticated_approver, now, ttl=300):
        if authenticated_approver not in self.approvers:
            raise PermissionError("approver is not authorized by the host")
        if not math.isfinite(now) or not math.isfinite(ttl) or not 0 < ttl <= 3600:
            raise ValueError("finite time and TTL in (0, 3600] required")
        binding = validate_snapshot(snapshot)
        token = secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("INSERT INTO approvals (token_hash,binding,approver,issued,expires) VALUES (?,?,?,?,?)",
                            (digest(token), binding, authenticated_approver, now, now + ttl))
        return token

    def consume(self, token, current_snapshot, now):
        binding = validate_snapshot(current_snapshot)
        if not isinstance(token, str) or not math.isfinite(now):
            raise ValueError("invalid token or time")
        # Atomic conditional update prevents concurrent/replayed consumption.
        with self.db:
            row = self.db.execute("SELECT approver FROM approvals WHERE token_hash=?", (digest(token),)).fetchone()
            if row is None or row[0] not in self.approvers:
                return False
            result = self.db.execute("UPDATE approvals SET consumed=1 WHERE token_hash=? AND binding=? AND consumed=0 AND issued<=? AND expires>?",
                                     (digest(token), binding, now, now))
            return result.rowcount == 1
