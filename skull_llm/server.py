"""Loopback-only SKULL-LLM live 3D web server (Python stdlib).

Serves the procedural WebGL client and streams bounded reasoning phases over
NDJSON. No hosted API, third-party scripts, remote listeners, or background bot.
"""
from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_MAX_JSON_BYTES = 16 * 1024
_ALLOWED_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/skull.css": ("skull.css", "text/css; charset=utf-8"),
    "/static/skull.js": ("skull.js", "text/javascript; charset=utf-8"),
    "/static/fallback.js": ("fallback.js", "text/javascript; charset=utf-8"),
}
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


def _default_status() -> dict[str, Any]:
    from .cli import doctor

    return doctor()


def _default_engine(*, depth: int, remember: bool, on_progress: Callable[[str, str], None]):
    from .runtime import SkullConfig, SkullEngine

    return SkullEngine(config=SkullConfig(depth=depth, remember=remember), on_progress=on_progress)


def make_handler(
    *,
    engine_factory: Callable[..., Any] = _default_engine,
    status_fn: Callable[[], dict[str, Any]] = _default_status,
):
    """A testable HTTP handler with injected inference/status dependencies."""

    class SkullHandler(BaseHTTPRequestHandler):
        server_version = "SKULL-LLM-local/0.1"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args) -> None:
            # Intentionally do not log user prompts or responses.
            if self.path.startswith("/api/chat"):
                return
            super().log_message(format, *args)

        def _host_allowed(self) -> bool:
            host = self.headers.get("Host", "").lower()
            hostname = urllib.parse.urlsplit("//" + host).hostname
            return hostname in {"localhost", "127.0.0.1", "::1"}

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            parsed = urllib.parse.urlsplit(origin)
            return parsed.scheme == "http" and parsed.hostname in {
                "localhost", "127.0.0.1", "::1"
            } and parsed.port == self.server.server_port

        def _header(self, code: int, content_type: str, length: int | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            if length is not None:
                self.send_header("Content-Length", str(length))
            for name, value in _SECURITY_HEADERS.items():
                self.send_header(name, value)
            if length is None:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = (json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8")
            self._header(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_allowed():
                self._json(403, {"error": "Localhost Host header required"})
                return
            path = urllib.parse.urlsplit(self.path).path
            if path == "/api/status":
                try:
                    self._json(200, status_fn())
                except Exception:
                    self._json(503, {"error": "Local model status unavailable"})
                return
            file_entry = _ALLOWED_FILES.get(path)
            if file_entry is None:
                self._json(404, {"error": "Not found"})
                return
            filename, content_type = file_entry
            try:
                data = (_STATIC_DIR / filename).read_bytes()
            except OSError:
                self._json(503, {"error": "Static interface unavailable"})
                return
            self._header(200, content_type, len(data))
            self.wfile.write(data)

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_allowed() or not self._origin_allowed():
                self._json(403, {"error": "Only same-origin local requests are accepted"})
                return
            if urllib.parse.urlsplit(self.path).path != "/api/chat":
                self._json(404, {"error": "Not found"})
                return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"error": "JSON body required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 1 or length > _MAX_JSON_BYTES:
                self._json(413, {"error": "Request body exceeds limit or is missing"})
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeError):
                self._json(400, {"error": "Invalid JSON"})
                return
            if not isinstance(payload, dict):
                self._json(400, {"error": "JSON object required"})
                return
            task = payload.get("task")
            depth = payload.get("depth", 2)
            remember = payload.get("remember", False)
            if not isinstance(task, str) or not 1 <= len(task.strip()) <= 8000:
                self._json(400, {"error": "Task must contain 1..8000 characters"})
                return
            if type(depth) is not int or depth not in (1, 2, 3):
                self._json(400, {"error": "Depth must be 1, 2 or 3"})
                return
            if type(remember) is not bool:
                self._json(400, {"error": "Remember must be true or false"})
                return

            self._header(200, "application/x-ndjson; charset=utf-8")
            try:
                def push(event: dict[str, Any]) -> None:
                    self.wfile.write((json.dumps(event, ensure_ascii=True) + "\n").encode("utf-8"))
                    self.wfile.flush()

                def progress(phase: str, message: str) -> None:
                    push({"type": "phase", "phase": phase, "message": message})

                engine = engine_factory(depth=depth, remember=remember, on_progress=progress)
                result = engine.run(task)
                push({"type": "answer", "answer": result.answer,
                      "calls": result.calls, "provenance": result.provenance,
                      "warnings": result.warnings})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                # Never serialize tracebacks or provider credentials.
                try:
                    message = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
                    push({"type": "error", "error": message[:400]})
                except (BrokenPipeError, ConnectionResetError):
                    pass

    return SkullHandler


def serve(*, host: str = "127.0.0.1", port: int = 7861) -> None:
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise ValueError("SKULL-LLM web interface must bind to loopback only")
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    server = ThreadingHTTPServer((host, port), make_handler())
    actual_port = server.server_address[1]
    print(f"SKULL-LLM 3D cockpit available at http://127.0.0.1:{actual_port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
