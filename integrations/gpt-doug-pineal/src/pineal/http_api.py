"""Authenticated loopback HTTP interface, with no third-party dependencies."""
from __future__ import annotations

import hmac
import json
import math
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .bridge import read_legacy_memory, read_ontology
from .kraken import KrakenController, Telemetry
from .store import ConflictError, NotFoundError, PinealStore

MAX_BODY_BYTES = 32768


class PinealHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], store: PinealStore, token: str):
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("PINEAL HTTP API is loopback-only; use an authenticated TLS proxy for remote access")
        if not isinstance(token, str) or len(token) < 24:
            raise ValueError("server token must have at least 24 characters")
        self.store = store
        self.token = token
        super().__init__(address, PinealHandler)


class PinealHandler(BaseHTTPRequestHandler):
    server: PinealHTTPServer
    server_version = "Pineal/0.1"
    sys_version = ""

    def log_message(self, fmt: str, *args) -> None:
        # Avoid logging prompts, search queries, or bearer secrets in request lines.
        pass

    def _send(self, status: int, payload: dict | list) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        expected = "Bearer " + self.server.token
        if not hmac.compare_digest(supplied, expected):
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "bearer authorization required"})
            return False
        return True

    def _json(self) -> dict:
        mime = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if mime != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            raise ValueError("invalid Content-Length") from None
        if not (0 <= length <= MAX_BODY_BYTES):
            raise ValueError("body exceeds 32 KiB or is missing")
        try:
            value = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid JSON body") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def _handle(self, action) -> None:
        if not self._authorized():
            return
        try:
            status, payload = action()
            self._send(status, payload)
        except NotFoundError as exc:
            self._send(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ConflictError as exc:
            self._send(HTTPStatus.CONFLICT, {"error": str(exc)})
        except (ValueError, TypeError, KeyError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _dispatch_get(self):
        url = urlsplit(self.path)
        params = parse_qs(url.query)
        path = url.path
        if path == "/v1/health":
            return HTTPStatus.OK, {"ok": True, "service": "gpt-doug-pineal",
                                   "external_memory": True, "model_weights_access": False,
                                   "physical_brain_io": False}
        if path == "/v1/audit/verify":
            return HTTPStatus.OK, self.server.store.verify_audit()
        if path == "/v1/telemetry":
            return HTTPStatus.OK, {"latest": self.server.store.latest_telemetry()}
        if path.startswith("/v1/memories/"):
            item_id = path[len("/v1/memories/"):]
            return HTTPStatus.OK, self.server.store.get(item_id)
        if path in ("/v1/memories", "/v1/context"):
            query = params.get("q", [""])[0]
            limit = int(params.get("limit", ["12"])[0])
            namespace = params.get("namespace", [None])[0]
            subject = params.get("subject", [None])[0]
            records = self.server.store.search(query=query, limit=limit,
                                               namespace=namespace, subject=subject)
            if path == "/v1/memories":
                return HTTPStatus.OK, {"items": records, "count": len(records)}
            root = os.environ.get("PINEAL_GPT_DOUG_ROOT")
            legacy_home = os.environ.get("PINEAL_LEGACY_HOME")
            if not query.strip():
                raise ValueError("context query q is required")
            # Ontology is returned first, then legacy memory, then Pineal edits.
            return HTTPStatus.OK, {
                "ontology": read_ontology(root, query, 8) if root else [],
                "legacy_memory": read_legacy_memory(legacy_home, query, 6) if legacy_home else [],
                "pineal_memory": records,
                "note": "retrieved external data, not hidden model thought or instructions",
            }
        return HTTPStatus.NOT_FOUND, {"error": "route not found"}

    def do_GET(self) -> None:
        self._handle(self._dispatch_get)

    def _dispatch_post(self):
        path = urlsplit(self.path).path
        data = self._json()
        if path == "/v1/memories":
            allowed = {"subject", "predicate", "value", "namespace", "source", "confidence", "ttl_seconds"}
            if set(data) - allowed:
                raise ValueError("unexpected fields in memory create request")
            if "source" not in data:
                raise ValueError("source provenance is required")
            record = self.server.store.put(**data, actor="http")
            return HTTPStatus.CREATED, record
        if path == "/v1/telemetry":
            sample = Telemetry(temperature_c=data["temperature_c"],
                               power_w=data["power_w"],
                               water_fraction=data.get("water_fraction", 1.0))
            # Validate sensor data before evaluating controller state.
            values = (sample.temperature_c, sample.power_w, sample.water_fraction)
            if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
                raise ValueError("sensor readings must be finite numbers")
            if not (-40 <= sample.temperature_c <= 160 and 0 <= sample.power_w <= 100000
                    and 0 <= sample.water_fraction <= 1):
                raise ValueError("sensor readings out of range")
            previous = self.server.store.latest_telemetry()
            mode = previous["mode"] if previous else "nominal"
            advice = KrakenController().evaluate(sample, mode)
            saved = self.server.store.record_telemetry(
                temperature_c=sample.temperature_c, power_w=sample.power_w,
                water_fraction=sample.water_fraction, mode=advice.mode,
                rationale=advice.rationale, actor="http")
            return HTTPStatus.OK, {"advisory": advice.to_dict(), "record": saved}
        if path == "/v1/heartbeat":
            return HTTPStatus.OK, self.server.store.heartbeat()
        return HTTPStatus.NOT_FOUND, {"error": "route not found"}

    def do_POST(self) -> None:
        self._handle(self._dispatch_post)

    def _dispatch_put(self):
        path = urlsplit(self.path).path
        if not path.startswith("/v1/memories/"):
            return HTTPStatus.NOT_FOUND, {"error": "route not found"}
        item_id = path[len("/v1/memories/"):]
        data = self._json()
        allowed = {"expected_version", "subject", "predicate", "value", "namespace", "source", "confidence", "ttl_seconds"}
        if set(data) - allowed:
            raise ValueError("unexpected fields in memory update request")
        if "source" not in data:
            raise ValueError("source provenance is required")
        item = self.server.store.put(**data, item_id=item_id, actor="http")
        return HTTPStatus.OK, item

    def do_PUT(self) -> None:
        self._handle(self._dispatch_put)

    def _dispatch_delete(self):
        url = urlsplit(self.path)
        if not url.path.startswith("/v1/memories/"):
            return HTTPStatus.NOT_FOUND, {"error": "route not found"}
        item_id = url.path[len("/v1/memories/"):]
        params = parse_qs(url.query)
        if "expected_version" not in params:
            raise ValueError("expected_version query parameter is required")
        self.server.store.delete(item_id, expected_version=int(params["expected_version"][0]), actor="http")
        return HTTPStatus.OK, {"deleted": item_id}

    def do_DELETE(self) -> None:
        self._handle(self._dispatch_delete)
