"""Kraken Credential Ontology: local, metadata-only credential lifecycle API.

A local register of operator-declared credential metadata, not a scanner, vault,
key generator, or tool for extending access. Rotation requires action at the
provider by an authorized human. No provider credentials are stored or returned.

Python 3.9+, standard library only. Run from repository root:
  python3 -m kraken_jutsu.credential_ontology init
  python3 -m kraken_jutsu.credential_ontology serve
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import secrets
import sqlite3
import stat
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

DEFAULT_STATE_DIR = Path.home() / ".gpt-doug" / "kraken-credential-ontology"
ALLOWED_KINDS = frozenset({
    "api-token", "iam-role", "github-app", "oauth-grant", "service-account",
    "workload-identity", "managed-identity", "other",
})
ALLOWED_OWNER_ROLES = frozenset({"operator", "security-officer", "developer", "service"})
ALLOWED_REASONS = frozenset({
    "scheduled", "suspected-compromise", "staff-change", "manual-review",
})
NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
ALIAS_RE = re.compile(r"^[a-z][a-z0-9_-]{2,47}$")
SECRETISH_RE = re.compile(
    r"(?:gh[pousr]_|sk[-_]|AKIA[0-9A-Z]{8}|ASIA[0-9A-Z]{8}|"
    r"xox[baprs]-|Bearer\s+|BEGIN[ -](?:RSA |EC |OPENSSH )?PRIVATE[ -]KEY|"
    r"api[_-]?key\s*[:=]|secret\s*[:=]|password\s*[:=])",
    re.IGNORECASE,
)
MAX_BODY = 4096

ONTOLOGY = {
    "ontology_id": "kraken-credential-governance-v1",
    "version": 1,
    "entities": {
        "CredentialMetadata": [
            "credential_id", "provider", "alias", "kind", "owner_role",
            "rotation_days", "expires_on", "local_status", "registered_at",
        ],
        "RotationRequest": ["request_id", "credential_id", "reason", "status", "requested_at"],
        "AuditEvent": ["sequence", "action", "object_id", "at"],
    },
    "relationships": [
        {"from": "RotationRequest", "to": "CredentialMetadata", "type": "REQUESTS_PROVIDER_ROTATION"},
        {"from": "AuditEvent", "to": "CredentialMetadata", "type": "RECORDS_METADATA_CHANGE"},
    ],
    "invariants": {
        "stores_secret_values": False,
        "reads_environment_secrets": False,
        "scans_repositories_for_keys": False,
        "issues_provider_credentials": False,
        "bypasses_revocation": False,
        "disables_security_patches": False,
        "provider_approval_required": True,
        "listens_on_loopback_only": True,
    },
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _require_plain_file(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or (info.st_mode & 0o077):
        raise ValueError("credential ontology files must be regular and owner-only")


def _secure_dir(path: Path) -> None:
    # An already-symlinked destination must fail rather than redirect local state.
    if path.is_symlink():
        raise ValueError("state directory may not be a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise ValueError("invalid state directory")
    if os.name == "posix":
        path.chmod(0o700)


def initialize(state_dir: Path = DEFAULT_STATE_DIR) -> dict[str, Any]:
    """Initialize a private local ledger and a separate, randomly generated API token."""
    directory = Path(state_dir)
    _secure_dir(directory)
    token_path = directory / "operator.token"
    if not token_path.exists() and not token_path.is_symlink():
        try:
            fd = os.open(str(token_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w", encoding="ascii") as out:
                out.write(secrets.token_urlsafe(48) + "\n")
    _require_plain_file(token_path)
    if len(token_path.read_text(encoding="ascii").strip()) < 32:
        raise ValueError("operator token is missing or too short")

    db_path = directory / "ontology.sqlite3"
    if not db_path.exists() and not db_path.is_symlink():
        try:
            fd = os.open(str(db_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
    _require_plain_file(db_path)
    with _connect(db_path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS credential_metadata (
              credential_id TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              alias TEXT NOT NULL,
              kind TEXT NOT NULL,
              owner_role TEXT NOT NULL,
              rotation_days INTEGER NOT NULL,
              expires_on TEXT,
              local_status TEXT NOT NULL,
              registered_at TEXT NOT NULL,
              UNIQUE(provider, alias)
            );
            CREATE TABLE IF NOT EXISTS rotation_requests (
              request_id TEXT PRIMARY KEY,
              credential_id TEXT NOT NULL REFERENCES credential_metadata(credential_id),
              reason TEXT NOT NULL,
              status TEXT NOT NULL,
              requested_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_pending_rotation
              ON rotation_requests (credential_id)
              WHERE status = 'PENDING_PROVIDER_APPROVAL';
            CREATE TABLE IF NOT EXISTS audit_events (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              action TEXT NOT NULL,
              object_id TEXT NOT NULL,
              at TEXT NOT NULL
            );
        """)
    return {"initialized": True, "state_dir": str(directory),
            "token_file": str(token_path), "api": "loopback_only",
            "secret_values_stored": False}


@contextlib.contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(str(db_path), timeout=5)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def _check_record(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("JSON object expected")
    valid = {"provider", "alias", "kind", "owner_role", "rotation_days", "expires_on"}
    required = valid - {"expires_on"}
    if set(payload) - valid or not required.issubset(payload):
        raise ValueError("unsupported or missing metadata fields; raw keys are prohibited")
    provider, alias = payload["provider"], payload["alias"]
    if not isinstance(provider, str) or not NAME_RE.fullmatch(provider):
        raise ValueError("invalid provider label")
    if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias) or SECRETISH_RE.search(alias):
        raise ValueError("invalid alias; raw credentials are prohibited")
    if not isinstance(payload["kind"], str) or payload["kind"] not in ALLOWED_KINDS:
        raise ValueError("invalid credential kind")
    if not isinstance(payload["owner_role"], str) or payload["owner_role"] not in ALLOWED_OWNER_ROLES:
        raise ValueError("invalid owner role")
    days = payload["rotation_days"]
    if type(days) is not int or not 1 <= days <= 365:
        raise ValueError("rotation_days must be an integer between 1 and 365")
    expires_on = payload.get("expires_on")
    if expires_on is not None:
        if not isinstance(expires_on, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expires_on):
            raise ValueError("expires_on must be a YYYY-MM-DD date or null")
        try:
            dt.date.fromisoformat(expires_on)
        except ValueError as exc:
            raise ValueError("invalid expires_on date") from exc
    return {**{key: payload[key] for key in required}, "expires_on": expires_on}


class CredentialOntology:
    """Only explicitly registered metadata; no secret/key discovery or issuance."""

    def __init__(self, state_dir: Path = DEFAULT_STATE_DIR):
        self.state_dir = Path(state_dir)
        self.token_path = self.state_dir / "operator.token"
        self.db_path = self.state_dir / "ontology.sqlite3"
        if not self.state_dir.is_dir() or self.state_dir.is_symlink():
            raise ValueError("run init first")
        _require_plain_file(self.token_path)
        _require_plain_file(self.db_path)

    def authenticate(self, header: str) -> bool:
        try:
            expected = self.token_path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            return False
        if not expected or len(expected) < 32 or not isinstance(header, str):
            return False
        return secrets.compare_digest(header, "Bearer " + expected)

    def register(self, data: Any) -> dict[str, Any]:
        fields = _check_record(data)
        row = {
            "credential_id": str(uuid.uuid4()),
            **fields,
            "local_status": "REGISTERED_PROVIDER_UNVERIFIED",
            "registered_at": _now(),
        }
        with _connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("""INSERT INTO credential_metadata
                    (credential_id, provider, alias, kind, owner_role,
                     rotation_days, expires_on, local_status, registered_at)
                    VALUES (:credential_id,:provider,:alias,:kind,:owner_role,
                            :rotation_days,:expires_on,:local_status,:registered_at)""", row)
            except sqlite3.IntegrityError as exc:
                raise ValueError("credential metadata alias already registered") from exc
            db.execute("INSERT INTO audit_events(action,object_id,at) VALUES (?,?,?)",
                       ("METADATA_REGISTERED", row["credential_id"], _now()))
        return row

    def credentials(self) -> list[dict[str, Any]]:
        with _connect(self.db_path) as db:
            return [dict(row) for row in db.execute("SELECT * FROM credential_metadata ORDER BY registered_at, credential_id")]

    def request_rotation(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or set(data) != {"credential_id", "reason"}:
            raise ValueError("credential_id and reason required; no secret fields allowed")
        credential_id, reason = data["credential_id"], data["reason"]
        try:
            uuid.UUID(credential_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("invalid credential_id") from exc
        if not isinstance(reason, str) or reason not in ALLOWED_REASONS:
            raise ValueError("invalid rotation reason")
        with _connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT local_status FROM credential_metadata WHERE credential_id=?",
                             (credential_id,)).fetchone()
            if row is None:
                raise ValueError("credential metadata not found")
            if row["local_status"] != "REGISTERED_PROVIDER_UNVERIFIED":
                raise ValueError("revoked metadata cannot request new credentials")
            existing = db.execute("SELECT * FROM rotation_requests WHERE credential_id=? AND status='PENDING_PROVIDER_APPROVAL'",
                                  (credential_id,)).fetchone()
            if existing is not None:
                return dict(existing)
            result = {"request_id": str(uuid.uuid4()), "credential_id": credential_id,
                      "reason": reason, "status": "PENDING_PROVIDER_APPROVAL",
                      "requested_at": _now()}
            db.execute("""INSERT INTO rotation_requests
                        (request_id, credential_id, reason, status, requested_at)
                        VALUES (:request_id,:credential_id,:reason,:status,:requested_at)""", result)
            db.execute("INSERT INTO audit_events(action,object_id,at) VALUES (?,?,?)",
                       ("PROVIDER_ROTATION_REQUESTED", result["request_id"], _now()))
            return result

    def requests(self) -> list[dict[str, Any]]:
        with _connect(self.db_path) as db:
            return [dict(row) for row in db.execute("SELECT * FROM rotation_requests ORDER BY requested_at, request_id")]

    def record_revocation(self, credential_id: Any) -> dict[str, Any]:
        try:
            uuid.UUID(credential_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid credential_id") from exc
        with _connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            found = db.execute("SELECT local_status FROM credential_metadata WHERE credential_id=?",
                               (credential_id,)).fetchone()
            if found is None:
                raise ValueError("credential metadata not found")
            if found["local_status"] != "REVOCATION_RECORDED_PROVIDER_UNVERIFIED":
                db.execute("UPDATE credential_metadata SET local_status=? WHERE credential_id=?",
                           ("REVOCATION_RECORDED_PROVIDER_UNVERIFIED", credential_id))
                db.execute("UPDATE rotation_requests SET status=? WHERE credential_id=? AND status=?",
                           ("CANCELLED_LOCAL_REVOCATION", credential_id, "PENDING_PROVIDER_APPROVAL"))
                db.execute("INSERT INTO audit_events(action,object_id,at) VALUES (?,?,?)",
                           ("LOCAL_REVOCATION_RECORDED", credential_id, _now()))
        return {"credential_id": credential_id, "local_status": "REVOCATION_RECORDED_PROVIDER_UNVERIFIED",
                "provider_revocation_performed": False}

    def audit(self) -> list[dict[str, Any]]:
        with _connect(self.db_path) as db:
            return [dict(row) for row in db.execute(
                "SELECT sequence, action, object_id, at FROM audit_events ORDER BY sequence DESC LIMIT 100")]


class KrakenAPI(BaseHTTPRequestHandler):
    """Authenticated loopback-only JSON gateway; no sensitive data endpoints."""

    server: "KrakenServer"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Never log bearer headers or request bodies.
        return

    def respond(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self) -> bool:
        if not self.server.ontology.authenticate(self.headers.get("Authorization", "")):
            self.respond(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self) -> None:
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        route = {
            "/v1/ontology": lambda: ONTOLOGY,
            "/v1/credentials": self.server.ontology.credentials,
            "/v1/rotation-requests": self.server.ontology.requests,
            "/v1/audit": self.server.ontology.audit,
        }.get(path)
        if route is None:
            self.respond(404, {"error": "not found"})
            return
        self.respond(200, {"data": route()})

    def do_POST(self) -> None:
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        if path not in {"/v1/credentials", "/v1/rotation-requests", "/v1/record-revocation"}:
            self.respond(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if length < 2 or length > MAX_BODY:
                raise ValueError("JSON request size outside allowed range")
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                raise ValueError("application/json required")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/v1/credentials":
                result = self.server.ontology.register(data)
            elif path == "/v1/rotation-requests":
                result = self.server.ontology.request_rotation(data)
            else:
                if not isinstance(data, dict) or set(data) != {"credential_id"}:
                    raise ValueError("credential_id required")
                result = self.server.ontology.record_revocation(data["credential_id"])
        except (ValueError, UnicodeError, json.JSONDecodeError, sqlite3.Error) as exc:
            # No user-provided text or secret values are reflected in errors.
            self.respond(400, {"error": "invalid_request", "reason": type(exc).__name__})
            return
        self.respond(200 if path != "/v1/credentials" else 201, {"data": result})


class KrakenServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, state_dir: Path, port: int = 8765, host: str = "127.0.0.1"):
        if host != "127.0.0.1":
            raise ValueError("only 127.0.0.1 is allowed")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("invalid port")
        self.ontology = CredentialOntology(state_dir)
        super().__init__((host, port), KrakenAPI)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize local metadata database and operator token")
    sub.add_parser("schema", help="print safe ontology schema without credentials")
    serve = sub.add_parser("serve", help="start authenticated local API")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            result = ONTOLOGY
        elif args.command == "init":
            result = initialize(args.state_dir)
        else:
            with KrakenServer(args.state_dir, port=args.port, host=args.host) as server:
                print(f"Kraken credential ontology (metadata-only) on http://127.0.0.1:{server.server_port}", flush=True)
                server.serve_forever(poll_interval=0.2)
            return 0
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": "local credential ontology unavailable"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
