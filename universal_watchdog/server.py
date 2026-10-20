"""Localhost-only authenticated oversight API and dashboard."""
from __future__ import annotations

import hmac
import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .core import Watchtower
from .policy import PolicyError
from .store import IntegrityFailure

MAX_BODY = 65536


class WatchtowerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, engine: Watchtower, operator_token: str,
                 ui_root: str | Path):
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("direct HTTP binding restricted to loopback; use an authenticated TLS reverse proxy")
        if len(operator_token) < 24:
            raise ValueError("operator token of at least 24 characters required")
        self.engine = engine
        self.operator_token = operator_token
        self.ui_root = Path(ui_root).resolve()
        if not (self.ui_root / "index.html").is_file():
            raise FileNotFoundError("Watchtower dashboard index.html missing")
        super().__init__(address, WatchtowerHandler)


class WatchtowerHandler(BaseHTTPRequestHandler):
    server: WatchtowerHTTPServer
    server_version = "XUNIA-Watchtower/1.0"

    def log_message(self, format, *args):
        # Avoid persisting request paths/tokens in access logs.
        return

    def _headers(self, status=200, type_="application/json; charset=utf-8", length=0):
        self.send_response(status)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()

    def _json(self, status, payload):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._headers(status, length=len(body))
        self.wfile.write(body)

    def _auth(self, role: str) -> bool:
        auth = self.headers.get("Authorization", "")
        token = self.server.operator_token
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], token):
            self._json(401, {"error": "authentication_required", "role": role})
            return False
        return True

    def _body(self) -> dict:
        size = self.headers.get("Content-Length", "")
        if not size.isdecimal() or not 0 < int(size) <= MAX_BODY:
            raise PolicyError("body length must be 1..65536")
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise PolicyError("application/json required")
        try:
            obj = json.loads(self.rfile.read(int(size)))
        except (ValueError, UnicodeDecodeError):
            raise PolicyError("malformed JSON") from None
        if not isinstance(obj, dict):
            raise PolicyError("JSON object expected")
        return obj

    def _guard(self, fn):
        try:
            fn()
        except (PolicyError, ValueError, TypeError) as exc:
            self._json(400, {"error": str(exc)[:180]})
        except PermissionError as exc:
            self._json(403, {"error": str(exc)[:150]})
        except (IntegrityFailure, OSError) as exc:
            self._json(503, {"error": "integrity_or_storage_failure", "action": "fail_closed"})

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/v1/health":
            self._json(200, {"service": "watchtower", "mode": "loopback", "status": "running"})
            return
        if path.startswith("/api/"):
            if not self._auth("operator"):
                return
            def read():
                eng = self.server.engine
                if path == "/api/v1/overview":
                    self._json(200, eng.overview())
                elif path == "/api/v1/events":
                    self._json(200, {"events": eng.store.list_decisions()})
                elif path == "/api/v1/pending":
                    self._json(200, {"decisions": eng.store.pending_reviews()})
                elif path == "/api/v1/approvals":
                    self._json(200, {"approvals": eng.store.list_approvals()})
                elif path == "/api/v1/ontology":
                    self._json(200, eng.ontology())
                elif path == "/api/v1/audit/verify":
                    result = eng.store.verify_chain()
                    self._json(200 if result["valid"] else 503, result)
                else:
                    self._json(404, {"error": "not_found"})
            self._guard(read)
            return
        if path in ("/", "/index.html"):
            target = self.server.ui_root / "index.html"
        elif path in ("/app.js", "/style.css", "/demo.json", "/ontology.json"):
            target = self.server.ui_root / path[1:]
        else:
            self._json(404, {"error": "not_found"})
            return
        try:
            data = target.read_bytes()
        except OSError:
            self._json(404, {"error": "not_found"})
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self._headers(200, content_type, len(data))
        self.wfile.write(data)

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        action_roles = {
            "/api/v1/evaluate": "model", "/api/v1/models": "operator",
            "/api/v1/approve": "operator", "/api/v1/stop": "operator",
            "/api/v1/rearm": "operator",
        }
        role = action_roles.get(path)
        if role is None:
            self._json(404, {"error": "not_found"})
            return
        if role == "operator" and not self._auth("operator"):
            return
        def dispatch():
            o = self._body()
            eng = self.server.engine
            if role == "model":
                candidate = self.headers.get("Authorization", "")
                candidate = candidate[7:] if candidate.startswith("Bearer ") else ""
                model_id = o.get("model_id", "")
                if not isinstance(model_id, str) or not eng.store.valid_model_token(model_id, candidate):
                    self._json(401, {"error": "model_authentication_required"})
                    return
            if path == "/api/v1/evaluate":
                payload = eng.evaluate(o)
                code = 200 if payload["enforce"] else 403 if payload["verdict"] == "deny" else 202
                self._json(code, payload)
            elif path == "/api/v1/models":
                self._json(201, eng.register(o))
            elif path == "/api/v1/approve":
                self._json(200, eng.approve(o.get("decision_id", ""), o.get("review_evidence_sha256", ""), o.get("ttl_seconds", 600)))
            elif path == "/api/v1/stop":
                self._json(200, eng.stop(o.get("reason", "operator_stop")))
            elif path == "/api/v1/rearm":
                self._json(200, eng.rearm(o.get("confirmation", "")))
        self._guard(dispatch)
