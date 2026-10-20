"""SQLite state and privacy-preserving HMAC audit chain."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import stat
import threading
import time
import uuid
from pathlib import Path


def canonical(x: object) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


class IntegrityFailure(RuntimeError):
    pass


class Store:
    def __init__(self, path: str | Path, audit_key: bytes):
        if len(audit_key) < 32:
            raise ValueError("audit key requires >= 32 bytes")
        self.key = audit_key
        self.path = Path(path).expanduser().absolute()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or (self.path.parent.stat().st_mode & 0o077):
            raise PermissionError("state directory must be private and not a symlink")
        if self.path.exists() and not stat.S_ISREG(self.path.lstat().st_mode):
            raise ValueError("database path must be a regular file (symlink forbidden)")
        self.conn = sqlite3.connect(self.path, timeout=5, check_same_thread=False, isolation_level="IMMEDIATE")
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.conn:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=FULL")
            self.conn.execute("PRAGMA busy_timeout=5000")
            self.conn.execute("PRAGMA secure_delete=ON")
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS models (
                  model_id TEXT PRIMARY KEY, provider TEXT NOT NULL, agent_id TEXT NOT NULL,
                  grants_json TEXT NOT NULL, scopes_json TEXT NOT NULL, token_hash TEXT NOT NULL,
                  created_at REAL NOT NULL, last_seen REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions (
                  id TEXT PRIMARY KEY, at REAL NOT NULL, model_id TEXT NOT NULL,
                  provider TEXT NOT NULL, agent_id TEXT NOT NULL, kind TEXT NOT NULL,
                  action TEXT NOT NULL, scope TEXT NOT NULL, resource TEXT NOT NULL,
                  verdict TEXT NOT NULL, risk TEXT NOT NULL, reason TEXT NOT NULL,
                  event_digest TEXT NOT NULL, trace_id TEXT NOT NULL,
                  approval_id TEXT NOT NULL, content_sha256 TEXT NOT NULL,
                  content_length INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals (
                  id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, event_digest TEXT NOT NULL,
                  state TEXT NOT NULL, approved_at REAL NOT NULL, expires_at REAL NOT NULL,
                  review_evidence_sha TEXT NOT NULL, consumed_at REAL);
                CREATE TABLE IF NOT EXISTS control (
                  id INTEGER PRIMARY KEY CHECK(id=1), stopped INTEGER NOT NULL,
                  reason TEXT NOT NULL, changed_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                  type TEXT NOT NULL, payload TEXT NOT NULL, prev_hash TEXT NOT NULL,
                  hash TEXT NOT NULL);
                INSERT OR IGNORE INTO control(id,stopped,reason,changed_at) VALUES(1,0,'initial',0);
            """)
        os.chmod(self.path, 0o600)
        self.assert_chain()

    def close(self):
        self.conn.close()

    def _audit(self, type_name: str, payload: dict):
        last = self.conn.execute("SELECT seq,hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        last_hash = last["hash"] if last else "0" * 64
        seq = int(last["seq"]) + 1 if last else 1
        at = time.time()
        body = canonical({"seq": seq, "at": at, "type": type_name, "payload": payload, "prev_hash": last_hash})
        digest = hmac.new(self.key, body.encode("utf-8"), hashlib.sha256).hexdigest()
        self.conn.execute("INSERT INTO audit(seq,at,type,payload,prev_hash,hash) VALUES (?,?,?,?,?,?)",
                          (seq, at, type_name, canonical(payload), last_hash, digest))
        return digest

    def verify_chain(self) -> dict:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM audit ORDER BY seq ASC").fetchall()
            prev = "0" * 64
            for expected_seq, row in enumerate(rows, 1):
                if row["seq"] != expected_seq or row["prev_hash"] != prev:
                    return {"valid": False, "records": len(rows), "error_at": expected_seq}
                try:
                    payload = json.loads(row["payload"])
                except (ValueError, TypeError):
                    return {"valid": False, "records": len(rows), "error_at": expected_seq}
                body = canonical({"seq": row["seq"], "at": row["at"], "type": row["type"],
                                  "payload": payload, "prev_hash": prev})
                actual = hmac.new(self.key, body.encode("utf-8"), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(actual, row["hash"]):
                    return {"valid": False, "records": len(rows), "error_at": expected_seq}
                prev = row["hash"]
            return {"valid": True, "records": len(rows), "last_hash": prev}

    def assert_chain(self):
        check = self.verify_chain()
        if not check["valid"]:
            raise IntegrityFailure("audit chain invalid; all controlled actions must stop")

    def register_model(self, model: dict):
        with self.lock, self.conn:
            self.assert_chain()
            now = time.time()
            self.conn.execute("""INSERT INTO models VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(model_id) DO UPDATE SET
                provider=excluded.provider, agent_id=excluded.agent_id,
                grants_json=excluded.grants_json, scopes_json=excluded.scopes_json,
                token_hash=excluded.token_hash, last_seen=excluded.last_seen""",
                (model["model_id"], model["provider"], model["agent_id"],
                 canonical(model["grants"]), canonical(model["scopes"]), model["token_hash"], now, now))
            self._audit("model.registration", {"model_id": model["model_id"], "provider": model["provider"],
                                               "agent_id": model["agent_id"], "grants": model["grants"],
                                               "scopes": model["scopes"]})

    def valid_model_token(self, model_id: str, candidate: str) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT token_hash FROM models WHERE model_id=?", (model_id,)).fetchone()
        hashed = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(row["token_hash"] if row else "0" * 64, hashed)

    def get_model(self, model_id: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM models WHERE model_id=?", (model_id,)).fetchone()
        if row is None:
            return None
        return {"model_id": row["model_id"], "provider": row["provider"],
                "agent_id": row["agent_id"], "grants": json.loads(row["grants_json"]),
                "scopes": json.loads(row["scopes_json"]), "last_seen": row["last_seen"]}

    def list_models(self) -> list[dict]:
        with self.lock:
            ids = [r["model_id"] for r in self.conn.execute("SELECT model_id FROM models ORDER BY model_id")]
        return [self.get_model(i) for i in ids]

    def stopped(self) -> dict:
        with self.lock:
            v = self.conn.execute("SELECT * FROM control WHERE id=1").fetchone()
        return {"stopped": bool(v["stopped"]), "reason": v["reason"], "changed_at": v["changed_at"]}

    def set_stop(self, stopped: bool, reason: str):
        with self.lock, self.conn:
            self.assert_chain()
            self.conn.execute("UPDATE control SET stopped=?,reason=?,changed_at=? WHERE id=1",
                              (int(stopped), reason[:100], time.time()))
            self._audit("control.stop" if stopped else "control.rearm", {"reason": reason[:100]})

    def store_decision(self, event: dict, verdict: str, reason: str, risk: str, approval_id: str = "") -> dict:
        decision_id = uuid.uuid4().hex
        now = time.time()
        public = {"decision_id": decision_id, "at": now, "model_id": event["model_id"],
                  "provider": event["provider"], "agent_id": event["agent_id"],
                  "kind": event["kind"], "action": event["action"], "scope": event["scope"],
                  "resource": event["resource"], "verdict": verdict, "reason": reason, "risk": risk,
                  "event_digest": event["event_digest"], "trace_id": event["trace_id"],
                  "approval_id": approval_id, "content_sha256": event["content_sha256"],
                  "content_length": event["content_length"]}
        with self.lock, self.conn:
            self.assert_chain()
            if verdict == "allow":
                self.conn.execute("UPDATE models SET last_seen=? WHERE model_id=? AND provider=? AND agent_id=?",
                                  (now, event["model_id"], event["provider"], event["agent_id"]))
            self.conn.execute("""INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (decision_id, now, event["model_id"], event["provider"], event["agent_id"],
                               event["kind"], event["action"], event["scope"], event["resource"], verdict,
                               risk, reason, event["event_digest"], event["trace_id"], approval_id,
                               event["content_sha256"], event["content_length"]))
            self._audit("guard.decision", public)
        return public

    def list_decisions(self, limit: int = 100) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM decisions ORDER BY at DESC LIMIT ?", (min(max(limit, 1), 200),)).fetchall()
        return [dict(x) for x in rows]

    def pending_reviews(self, limit: int = 100) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("""SELECT d.* FROM decisions d
              WHERE d.verdict='review' AND NOT EXISTS (
                SELECT 1 FROM approvals a WHERE a.decision_id=d.id AND a.state IN ('active','used'))
              ORDER BY d.at DESC LIMIT ?""", (min(max(limit, 1), 200),)).fetchall()
        return [dict(x) for x in rows]

    def counts(self) -> dict:
        with self.lock:
            cs = dict(self.conn.execute("SELECT verdict,COUNT(*) FROM decisions GROUP BY verdict").fetchall())
            count = self.conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
            pending = self.conn.execute("""SELECT COUNT(*) FROM decisions d
              WHERE d.verdict='review' AND NOT EXISTS (
                SELECT 1 FROM approvals a WHERE a.decision_id=d.id AND a.state IN ('active','used'))""").fetchone()[0]
        return {"models": count, "decisions": sum(cs.values()), "allowed": cs.get("allow", 0),
                "denied": cs.get("deny", 0), "reviewed": pending}

    def approve(self, decision_id: str, evidence_sha: str, ttl: int = 600) -> dict:
        with self.lock, self.conn:
            self.assert_chain()
            row = self.conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
            if row is None or row["verdict"] != "review":
                raise ValueError("only an existing review decision can be approved")
            if self.conn.execute("SELECT 1 FROM approvals WHERE decision_id=? AND state IN ('active','used')", (decision_id,)).fetchone():
                raise ValueError("decision already approved")
            now = time.time()
            ident = uuid.uuid4().hex
            self.conn.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)",
                              (ident, decision_id, row["event_digest"], "active", now, now + ttl, evidence_sha, None))
            self._audit("review.approved", {"approval_id": ident, "decision_id": decision_id,
                                            "evidence_sha256": evidence_sha, "expires_at": now + ttl})
            return {"approval_id": ident, "decision_id": decision_id, "expires_at": now + ttl,
                    "state": "active"}

    def consume_approval(self, approval_id: str, digest: str) -> bool:
        with self.lock, self.conn:
            self.assert_chain()
            row = self.conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if not row or row["state"] != "active" or row["event_digest"] != digest or row["expires_at"] < time.time():
                return False
            now = time.time()
            updated = self.conn.execute("UPDATE approvals SET state='used',consumed_at=? WHERE id=? AND state='active'",
                                        (now, approval_id)).rowcount
            if not updated:
                return False
            self._audit("review.consumed", {"approval_id": approval_id, "event_digest": digest})
            return True

    def list_approvals(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM approvals ORDER BY approved_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(x) for x in rows]
