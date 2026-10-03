"""Streaming GPT-Doug browser bridge.

This module preserves the bounded/authenticated behavior from ``wakeup3lm.bridge``
and adds an NDJSON streaming route at ``POST /api/chat/stream``. Existing
``/health``, ``/api/tags`` and non-streaming ``/api/chat`` behavior remains
available through the inherited handler.
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from .bridge import (
    MAX_RESPONSE,
    PROJECT_RE,
    BridgeConfig,
    BridgeHandler,
    BridgeServer,
    NoRedirects,
    ResponseCache,
    UpstreamUnavailable,
    _chat_payload,
)


def _stream_payload(config: BridgeConfig, raw: object) -> dict:
    if not isinstance(raw, dict) or raw.get("stream") is not True:
        raise ValueError("streaming requests require stream:true")
    normalized_input = dict(raw)
    normalized_input["stream"] = False
    payload = _chat_payload(config, normalized_input)
    payload["stream"] = True
    return payload


class StreamingBridgeServer(BridgeServer):
    """Bridge server using the streaming-aware request handler."""

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.cache = ResponseCache(config)
        self.capacity = threading.BoundedSemaphore(config.concurrency)
        if ":" in config.host:
            self.address_family = socket.AF_INET6
        ThreadingHTTPServer.__init__(
            self,
            (config.host, config.port),
            StreamingBridgeHandler,
        )


class StreamingBridgeHandler(BridgeHandler):
    protocol_version = "HTTP/1.1"

    def _stream_headers(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Doug-Stream", "ndjson")
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin in self.server.config.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization, X-Doug-Project",
            )
            self.send_header(
                "Access-Control-Expose-Headers",
                "X-Doug-Cache, X-Doug-Stream",
            )
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _stream_event(self, payload: dict) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        self.wfile.write(encoded)
        self.wfile.flush()

    def do_OPTIONS(self):
        path = urlsplit(self.path).path
        if path != "/api/chat/stream":
            return super().do_OPTIONS()
        if not self._authorize(preflight=True):
            return
        method = self.headers.get("Access-Control-Request-Method", "GET")
        requested = {
            header.strip().lower()
            for header in self.headers.get(
                "Access-Control-Request-Headers", ""
            ).split(",")
            if header.strip()
        }
        if method != "POST" or requested - {
            "authorization",
            "content-type",
            "x-doug-project",
        }:
            return self._send(
                403,
                {"error": "requested method or headers are not allowed"},
            )
        self._send(200, {"ok": True, "stream": "ndjson"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/chat/stream":
            return super().do_POST()
        if not self._authorize():
            return

        try:
            payload = _stream_payload(self.server.config, self._read_json())
            project = self.headers.get("X-Doug-Project", "")
            if project and not PROJECT_RE.fullmatch(project):
                raise ValueError("invalid project scope")
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})

        if not self.server.capacity.acquire(blocking=False):
            return self._send(
                429,
                {"error": "the local model is busy; retry after the running request completes"},
            )

        headers_sent = False
        try:
            request = urllib.request.Request(
                self.server.config.ollama_url.rstrip("/") + "/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                NoRedirects(),
            )
            with opener.open(
                request,
                timeout=self.server.config.timeout,
            ) as response:
                self._stream_headers()
                headers_sent = True
                total = 0
                completed = False
                while True:
                    line = response.readline(MAX_RESPONSE + 1)
                    if not line:
                        break
                    total += len(line)
                    if total > MAX_RESPONSE:
                        raise UpstreamUnavailable(
                            "model response exceeded the bridge limit"
                        )
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise UpstreamUnavailable(
                            "Ollama returned invalid streaming JSON"
                        ) from exc
                    if not isinstance(chunk, dict) or chunk.get("error"):
                        raise UpstreamUnavailable(
                            "Ollama returned an invalid streaming response"
                        )
                    message = chunk.get("message")
                    if message is not None and (
                        not isinstance(message, dict)
                        or not isinstance(message.get("content", ""), str)
                    ):
                        raise UpstreamUnavailable(
                            "Ollama returned invalid streaming message content"
                        )
                    if chunk.get("done") is True:
                        completed = True
                    chunk["bridge"] = "black-house"
                    chunk["cached"] = False
                    self._stream_event(chunk)

                if not completed:
                    raise UpstreamUnavailable(
                        "model streaming generation did not finish"
                    )
        except (
            urllib.error.URLError,
            OSError,
            ValueError,
            TimeoutError,
            UpstreamUnavailable,
        ):
            message = "Ollama is unavailable or returned an invalid streaming response"
            if headers_sent:
                try:
                    self._stream_event(
                        {
                            "error": message,
                            "done": True,
                            "bridge": "black-house",
                        }
                    )
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
            else:
                self._send(503, {"error": message})
        finally:
            self.server.capacity.release()


def main() -> None:
    try:
        config = BridgeConfig.from_env()
        server = StreamingBridgeServer(config)
    except (ValueError, OSError):
        raise SystemExit(
            "Streaming bridge configuration or bind failed; check DOUG_BRIDGE_* settings."
        ) from None

    print(
        f"Black House streaming bridge listening on port {server.server_port}; "
        f"{len(config.origins)} browser origin(s) allowed."
    )
    print(
        "Routes: /health, /api/tags, /api/chat, /api/chat/stream (NDJSON)."
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
