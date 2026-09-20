from __future__ import annotations

import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .protocol import canonical_json, sign, verify

MAX_BODY_BYTES = 64 * 1024
NONCE_TTL_SECONDS = 300


class BodyNodeState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.nonces: dict[str, int] = {}
        self.controller_id: str | None = None
        self.hive_id: str | None = None
        self.ontology_hash: str | None = None
        self.last_handshake_at: int | None = None
        self.last_heartbeat_at: int | None = None

    def claim_nonce(self, nonce: str) -> bool:
        now = int(time.time())
        with self.lock:
            self.nonces = {key: seen for key, seen in self.nonces.items() if now - seen < NONCE_TTL_SECONDS}
            if len(self.nonces) > 10000:
                oldest = sorted(self.nonces.items(), key=lambda item: item[1])[:1000]
                for key, _seen in oldest:
                    self.nonces.pop(key, None)
            if nonce in self.nonces:
                return False
            self.nonces[nonce] = now
            return True


STATE = BodyNodeState()


def _key() -> str:
    secret = os.getenv("GPT_DOUG_BODY_LINK_KEY", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("GPT_DOUG_BODY_LINK_KEY must be configured with at least 32 bytes")
    return secret


def _node_id() -> str:
    return os.getenv(
        "GPT_DOUG_BODY_NODE_ID",
        "replit:24kmediaproduct/GPT-Doug-AI-Hub",
    ).strip() or "replit:24kmediaproduct/GPT-Doug-AI-Hub"


def _capabilities() -> list[str]:
    return [
        "AUTHENTICATED_HANDSHAKE",
        "SIGNED_HEARTBEAT",
        "NODE_IDENTITY",
        "HIVE_PROVENANCE",
        "READ_ONLY_BODY_STATUS",
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "GPTDougBody/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, path: str, payload: dict[str, Any]) -> None:
        body = canonical_json(payload)
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = sign(
            _key(),
            method="RESPONSE",
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-GPTDoug-Protocol", "gptdoug-body-link-v1")
        self.send_header("X-GPTDoug-Timestamp", timestamp)
        self.send_header("X-GPTDoug-Nonce", nonce)
        self.send_header("X-GPTDoug-Signature", signature)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        body = canonical_json(
            {
                "status": "ONLINE",
                "body_node_id": _node_id(),
                "protocol": "gptdoug-body-link-v1",
                "remote_shell": False,
            }
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path not in {"/v1/handshake", "/v1/heartbeat"}:
            self.send_error(404)
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if size <= 0 or size > MAX_BODY_BYTES:
            self.send_error(413)
            return

        body = self.rfile.read(size)
        timestamp = self.headers.get("X-GPTDoug-Timestamp", "")
        nonce = self.headers.get("X-GPTDoug-Nonce", "")
        signature = self.headers.get("X-GPTDoug-Signature", "")

        if not nonce or not STATE.claim_nonce(nonce):
            self._send(409, self.path, {"error": "REPLAY_OR_MISSING_NONCE"})
            return
        if not verify(
            _key(),
            method="POST",
            path=self.path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            signature=signature,
        ):
            self._send(401, self.path, {"error": "SIGNATURE_VERIFICATION_FAILED"})
            return

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, self.path, {"error": "INVALID_JSON"})
            return
        if not isinstance(payload, dict):
            self._send(400, self.path, {"error": "INVALID_PAYLOAD"})
            return

        controller_id = str(payload.get("controller_id", "")).strip()
        if controller_id != "GPT_DOUG":
            self._send(403, self.path, {"error": "CONTROLLER_NOT_ALLOWED"})
            return

        now = int(time.time())
        with STATE.lock:
            STATE.controller_id = controller_id
            STATE.hive_id = payload.get("hive_id")
            STATE.ontology_hash = payload.get("ontology_hash")

            if self.path == "/v1/handshake":
                STATE.last_handshake_at = now
                response = {
                    "protocol": "gptdoug-body-link-v1",
                    "linked": True,
                    "controller_id": controller_id,
                    "body_node_id": _node_id(),
                    "challenge": payload.get("challenge"),
                    "capabilities": _capabilities(),
                    "remote_shell": False,
                    "last_handshake_at": now,
                }
            else:
                STATE.last_heartbeat_at = now
                response = {
                    "protocol": "gptdoug-body-link-v1",
                    "linked": True,
                    "controller_id": controller_id,
                    "body_node_id": _node_id(),
                    "capabilities": _capabilities(),
                    "status": "ONLINE",
                    "remote_shell": False,
                    "last_heartbeat_at": now,
                }

        self._send(200, self.path, response)


def main() -> int:
    host = os.getenv("GPT_DOUG_BODY_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("GPT_DOUG_BODY_PORT", "3000")))
    _key()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"GPT-DOUG BODY NODE // ONLINE // {_node_id()} // {host}:{port}")
    print("REMOTE SHELL // DISABLED")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
