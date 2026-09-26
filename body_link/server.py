from __future__ import annotations

import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .protocol import canonical_json, sign, verify
from .state import runtime_body_state, sanitize_body_state

MAX_BODY_BYTES = 64 * 1024
NONCE_TTL_SECONDS = 300


class BodyNodeState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.nonces: dict[str, int] = {}
        self.controller_id: str | None = None
        self.hive_id: str | None = None
        self.ontology_hash: str | None = None
        self.last_handshake_at: int | None = None
        self.last_heartbeat_at: int | None = None
        self.body_state: dict[str, Any] = runtime_body_state("IDLE", "body node online")
        self.state_version = 0

    def claim_nonce(self, nonce: str) -> bool:
        now = int(time.time())
        with self.lock:
            self.nonces = {
                key: seen
                for key, seen in self.nonces.items()
                if now - seen < NONCE_TTL_SECONDS
            }
            if len(self.nonces) > 10000:
                oldest = sorted(self.nonces.items(), key=lambda item: item[1])[:1000]
                for key, _seen in oldest:
                    self.nonces.pop(key, None)
            if nonce in self.nonces:
                return False
            self.nonces[nonce] = now
            return True

    def set_body_state(self, payload: Any) -> tuple[int, dict[str, Any]]:
        sanitized = sanitize_body_state(payload)
        with self.condition:
            self.body_state = sanitized
            self.state_version += 1
            version = self.state_version
            self.condition.notify_all()
            return version, dict(sanitized)

    def snapshot(self) -> tuple[int, dict[str, Any]]:
        with self.lock:
            return self.state_version, dict(self.body_state)


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
        "SIGNED_BODY_STATE_PUSH",
        "BODY_STATE_SNAPSHOT",
        "SSE_BODY_STATE_STREAM",
        "LEARN_STATE",
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "GPTDougBody/2.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    @property
    def route_path(self) -> str:
        return self.path.split("?", 1)[0]

    def _send_signed(self, status: int, path: str, payload: dict[str, Any]) -> None:
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

    def _send_public_json(self, status: int, payload: dict[str, Any]) -> None:
        body = canonical_json(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _stream_state(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_version = -1
        while True:
            with STATE.condition:
                if STATE.state_version == last_version:
                    STATE.condition.wait(timeout=15.0)
                version = STATE.state_version
                state = dict(STATE.body_state)

            if version == last_version:
                payload = ": heartbeat\n\n"
            else:
                data = json.dumps(
                    {
                        "state_version": version,
                        "body_state": state,
                    },
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                payload = (
                    f"id: {version}\n"
                    "event: body_state\n"
                    f"data: {data}\n\n"
                )
                last_version = version

            try:
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

    def do_GET(self) -> None:
        path = self.route_path

        if path == "/health":
            self._send_public_json(
                200,
                {
                    "status": "ONLINE",
                    "service": "GPT-Doug-AI-Hub",
                    "body_node_id": _node_id(),
                    "protocol": "gptdoug-body-link-v1",
                    "body_link_version": 2,
                    "remote_shell": False,
                    "capabilities": _capabilities(),
                },
            )
            return

        if path == "/v1/state":
            version, state = STATE.snapshot()
            self._send_public_json(
                200,
                {
                    "state_version": version,
                    "body_state": state,
                },
            )
            return

        if path == "/v1/stream":
            self._stream_state()
            return

        self.send_error(404)

    def do_POST(self) -> None:
        path = self.route_path
        if path not in {"/v1/handshake", "/v1/heartbeat", "/v1/state"}:
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
            self._send_signed(409, path, {"error": "REPLAY_OR_MISSING_NONCE"})
            return
        if not verify(
            _key(),
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            signature=signature,
        ):
            self._send_signed(401, path, {"error": "SIGNATURE_VERIFICATION_FAILED"})
            return

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_signed(400, path, {"error": "INVALID_JSON"})
            return
        if not isinstance(payload, dict):
            self._send_signed(400, path, {"error": "INVALID_PAYLOAD"})
            return

        controller_id = str(payload.get("controller_id", "")).strip()
        if controller_id != "GPT_DOUG":
            self._send_signed(403, path, {"error": "CONTROLLER_NOT_ALLOWED"})
            return

        now = int(time.time())
        with STATE.lock:
            STATE.controller_id = controller_id
            STATE.hive_id = payload.get("hive_id")
            STATE.ontology_hash = payload.get("ontology_hash")

        if path == "/v1/handshake":
            with STATE.lock:
                STATE.last_handshake_at = now
            self._send_signed(
                200,
                path,
                {
                    "protocol": "gptdoug-body-link-v1",
                    "body_link_version": 2,
                    "linked": True,
                    "controller_id": controller_id,
                    "body_node_id": _node_id(),
                    "challenge": payload.get("challenge"),
                    "capabilities": _capabilities(),
                    "remote_shell": False,
                    "last_handshake_at": now,
                },
            )
            return

        if path == "/v1/heartbeat":
            with STATE.lock:
                STATE.last_heartbeat_at = now
            self._send_signed(
                200,
                path,
                {
                    "protocol": "gptdoug-body-link-v1",
                    "body_link_version": 2,
                    "linked": True,
                    "controller_id": controller_id,
                    "body_node_id": _node_id(),
                    "capabilities": _capabilities(),
                    "status": "ONLINE",
                    "remote_shell": False,
                    "last_heartbeat_at": now,
                },
            )
            return

        try:
            version, state = STATE.set_body_state(payload.get("body_state"))
        except ValueError as exc:
            self._send_signed(
                400,
                path,
                {
                    "error": "INVALID_BODY_STATE",
                    "detail": str(exc)[:160],
                },
            )
            return

        self._send_signed(
            200,
            path,
            {
                "protocol": "gptdoug-body-link-v1",
                "accepted": True,
                "body_node_id": _node_id(),
                "state_version": version,
                "state": state.get("state"),
                "remote_shell": False,
            },
        )


def main() -> int:
    host = os.getenv("GPT_DOUG_BODY_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("GPT_DOUG_BODY_PORT", "3000")))
    _key()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"GPT-DOUG BODY NODE // ONLINE // {_node_id()} // {host}:{port}")
    print("BODY-LINK // V2 STATE STREAM")
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
