"""A bounded, single-owner browser bridge to an administrator's Ollama service.

Run ``python3 -m wakeup3lm.bridge`` from the repository checkout. This does not
provide cloud compute, issue tokens, or circumvent any provider's limits. Browser
origins must be explicitly allowed; a bearer token is required on network binds.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

MAX_BODY = 256 * 1024
MAX_RESPONSE = 2 * 1024 * 1024
MAX_INPUT_CHARS = 24_000
MAX_OUTPUT_TOKENS = 2_048
MAX_CONTEXT_TOKENS = 8_192
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z")
PROJECT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _model_key(name: str) -> str:
    return name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"


@dataclass(frozen=True)
class BridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8791
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:7b"
    models: tuple[str, ...] = ()
    origins: tuple[str, ...] = ()
    token: str = field(default="", repr=False)
    timeout: float = 120.0
    cache_ttl: float = 300.0
    cache_entries: int = 64
    cache_bytes: int = 16 * 1024 * 1024
    concurrency: int = 2

    def __post_init__(self) -> None:
        if not self.host or not 0 <= self.port <= 65535:
            raise ValueError("invalid bridge bind address")
        if not _loopback(self.host) and len(self.token) < 24:
            raise ValueError("non-loopback binds require DOUG_BRIDGE_TOKEN of at least 24 characters")
        if any(ord(char) < 32 for char in self.token):
            raise ValueError("invalid bridge token")
        upstream = urlsplit(self.ollama_url)
        if (upstream.scheme not in {"http", "https"} or not upstream.hostname
                or upstream.username or upstream.password or upstream.query or upstream.fragment
                or upstream.path not in {"", "/"}):
            raise ValueError("Ollama URL must be an HTTP(S) base URL without credentials or a path")
        if upstream.scheme == "http" and not _loopback(upstream.hostname):
            raise ValueError("non-loopback Ollama upstreams require HTTPS")
        if not MODEL_RE.fullmatch(self.model):
            raise ValueError("invalid default model")
        if any(not MODEL_RE.fullmatch(model) for model in self.allowed_models):
            raise ValueError("invalid model allowlist")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path or parsed.query
                    or parsed.fragment or "*" in origin or any(ord(char) < 33 for char in origin)
                    or (parsed.scheme == "http" and not _loopback(parsed.hostname))):
                raise ValueError("origins must be exact HTTPS origins (HTTP is allowed on loopback)")
        if not 0 < self.timeout <= 180 or not 0 <= self.cache_ttl <= 3600:
            raise ValueError("invalid bridge timeout or cache lifetime")
        if not 0 <= self.cache_entries <= 256 or not 0 <= self.cache_bytes <= 64 * 1024 * 1024:
            raise ValueError("invalid cache bounds")
        if not 1 <= self.concurrency <= 8:
            raise ValueError("invalid inference concurrency")

    @property
    def allowed_models(self) -> tuple[str, ...]:
        return self.models or (self.model,)

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        return cls(
            host=os.environ.get("DOUG_BRIDGE_HOST", "127.0.0.1"),
            port=int(os.environ.get("DOUG_BRIDGE_PORT", "8791")),
            ollama_url=os.environ.get("DOUG_BRIDGE_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=os.environ.get("DOUG_BRIDGE_MODEL", "qwen2.5-coder:7b"),
            models=tuple(filter(None, (s.strip() for s in os.environ.get("DOUG_BRIDGE_MODELS", "").split(",")))),
            origins=tuple(filter(None, (s.strip() for s in os.environ.get("DOUG_BRIDGE_ORIGINS", "").split(",")))),
            token=os.environ.get("DOUG_BRIDGE_TOKEN", ""),
        )


class ResponseCache:
    """Bounded, expiring responses; prompts are represented only by a hash key."""

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.items: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self.size = 0
        self.lock = threading.Lock()

    def _prune(self, now: float) -> None:
        for key in list(self.items):
            if self.items[key][0] <= now:
                self.size -= len(self.items.pop(key)[1])

    def get(self, key: str) -> dict | None:
        with self.lock:
            self._prune(time.monotonic())
            entry = self.items.get(key)
            if entry is None:
                return None
            self.items.move_to_end(key)
            return json.loads(entry[1])

    def put(self, key: str, payload: dict) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if (not self.config.cache_entries or not self.config.cache_ttl
                or len(encoded) > self.config.cache_bytes):
            return
        with self.lock:
            self._prune(time.monotonic())
            old = self.items.pop(key, None)
            if old:
                self.size -= len(old[1])
            while self.items and (len(self.items) >= self.config.cache_entries
                                  or self.size + len(encoded) > self.config.cache_bytes):
                self.size -= len(self.items.popitem(last=False)[1][1])
            self.items[key] = (time.monotonic() + self.config.cache_ttl, encoded)
            self.size += len(encoded)


class UpstreamUnavailable(Exception):
    pass


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _upstream(config: BridgeConfig, path: str, payload: dict | None = None) -> dict:
    # A fixed, administrator-configured host and fixed API paths only. Never
    # forward the browser's token, proxy environment, or upstream redirects.
    request = urllib.request.Request(
        config.ollama_url.rstrip("/") + path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())
    try:
        with opener.open(request, timeout=min(config.timeout, 10) if payload is None else config.timeout) as response:
            encoded = response.read(MAX_RESPONSE + 1)
        if len(encoded) > MAX_RESPONSE:
            raise UpstreamUnavailable("model response exceeded the bridge limit")
        body = json.loads(encoded)
        if not isinstance(body, dict) or body.get("error"):
            raise UpstreamUnavailable("Ollama returned an invalid response")
        return body
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        # Upstream errors can contain URLs, prompts, or credentials. Keep them
        # out of both browser errors and the request log.
        raise UpstreamUnavailable("Ollama is unavailable or returned an invalid response") from exc


def _installed_models(config: BridgeConfig) -> list[dict]:
    payload = _upstream(config, "/api/tags")
    models = payload.get("models")
    if not isinstance(models, list):
        raise UpstreamUnavailable("Ollama returned an invalid model list")
    allowed = {_model_key(name) for name in config.allowed_models}
    result = []
    for model in models:
        name = model.get("name") if isinstance(model, dict) else None
        if isinstance(name, str) and _model_key(name) in allowed:
            result.append({"name": name, "model": name})
    return result


def _chat_payload(config: BridgeConfig, raw: Any) -> dict:
    if not isinstance(raw, dict) or set(raw) - {"model", "messages", "stream", "options", "format"}:
        raise ValueError("expected model, messages, stream, options, and optional format fields")
    model = raw.get("model", config.model)
    if not isinstance(model, str) or _model_key(model) not in {_model_key(m) for m in config.allowed_models}:
        raise ValueError("model is not allowed by this bridge")
    if raw.get("stream", False) is not False:
        raise ValueError("this bridge supports stream:false only")
    messages = raw.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
        raise ValueError("messages must contain between 1 and 64 messages")
    count = 0
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or not isinstance(message["role"], str)
                or message["role"] not in {"system", "user", "assistant"}
                or not isinstance(message["content"], str)):
            raise ValueError("messages require a supported role and text content")
        count += len(message["content"])
    if count > MAX_INPUT_CHARS:
        raise ValueError(f"message content exceeds {MAX_INPUT_CHARS} characters")
    options = raw.get("options", {})
    if not isinstance(options, dict) or set(options) - {"temperature", "top_p", "seed", "num_predict", "num_ctx"}:
        raise ValueError("unsupported model options")
    normalized = {"temperature": 0.25, "num_predict": MAX_OUTPUT_TOKENS, "num_ctx": MAX_CONTEXT_TOKENS, **options}
    for name, ceiling in (("num_predict", MAX_OUTPUT_TOKENS), ("num_ctx", MAX_CONTEXT_TOKENS)):
        if type(normalized[name]) is not int or not 1 <= normalized[name] <= ceiling:
            raise ValueError(f"{name} must be an integer between 1 and {ceiling}")
    for name, ceiling in (("temperature", 2), ("top_p", 1)):
        if name in normalized and (type(normalized[name]) not in {int, float}
                                   or not math.isfinite(normalized[name])
                                   or not 0 <= normalized[name] <= ceiling):
            raise ValueError(f"{name} is out of range")
    if "seed" in normalized and (type(normalized["seed"]) is not int or not 0 <= normalized["seed"] <= 2**31 - 1):
        raise ValueError("seed must be an integer between 0 and 2147483647")
    result = {"model": model, "messages": messages, "stream": False, "options": normalized}
    if "format" in raw:
        if raw["format"] != "json":
            raise ValueError("format must be json when supplied")
        result["format"] = "json"
    return result


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.cache = ResponseCache(config)
        self.capacity = threading.BoundedSemaphore(config.concurrency)
        if ":" in config.host:
            self.address_family = socket.AF_INET6
        super().__init__((config.host, config.port), BridgeHandler)

    def handle_error(self, request, client_address):
        # Request bodies and secret-bearing headers must never be logged.
        pass


class BridgeHandler(BaseHTTPRequestHandler):
    server: BridgeServer

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, fmt, *args):
        pass

    def _send(self, status: int, payload: dict, *, cache: str | None = None):
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin in self.server.config.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Doug-Project")
            self.send_header("Access-Control-Expose-Headers", "X-Doug-Cache")
            if self.command == "OPTIONS" and self.headers.get("Access-Control-Request-Private-Network") == "true":
                self.send_header("Access-Control-Allow-Private-Network", "true")
        if cache:
            self.send_header("X-Doug-Cache", cache)
        self.end_headers()
        if encoded:
            self.wfile.write(encoded)

    def _authorize(self, *, preflight: bool = False) -> bool:
        config = self.server.config
        origin = self.headers.get("Origin")
        if origin is not None and origin not in config.origins:
            self._send(403, {"error": "browser origin is not allowed"})
            return False
        # Reject DNS rebinding when a loopback bridge does not have a token.
        try:
            host = urlsplit("http://" + self.headers.get("Host", "")).hostname or ""
        except ValueError:
            host = ""
        if _loopback(config.host) and not config.token and not _loopback(host):
            self._send(403, {"error": "invalid bridge host"})
            return False
        if not preflight and config.token:
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), ("Bearer " + config.token).encode()):
                self._send(401, {"error": "bridge bearer token is required"})
                return False
        return True

    def do_OPTIONS(self):
        if not self._authorize(preflight=True):
            return
        if urlsplit(self.path).path not in {"/health", "/api/tags", "/api/chat"}:
            return self._send(404, {"error": "not found"})
        method = self.headers.get("Access-Control-Request-Method", "GET")
        requested = {h.strip().lower() for h in self.headers.get("Access-Control-Request-Headers", "").split(",") if h.strip()}
        if method not in {"GET", "POST"} or requested - {"authorization", "content-type", "x-doug-project"}:
            return self._send(403, {"error": "requested method or headers are not allowed"})
        self._send(200, {"ok": True})

    def do_GET(self):
        if not self._authorize():
            return
        path = urlsplit(self.path).path
        if path not in {"/health", "/api/tags"}:
            return self._send(404, {"error": "not found"})
        try:
            models = _installed_models(self.server.config)
            if path == "/api/tags":
                return self._send(200, {"models": models, "bridge": "black-house"})
            ready = any(_model_key(model["name"]) == _model_key(self.server.config.model) for model in models)
            return self._send(200 if ready else 503, {
                "ok": ready, "bridge": "black-house", "model": self.server.config.model,
                "model_ready": ready, "inference_verified": False,
                "detail": "Model is installed; health does not run generation." if ready else "Configured model is not installed or allowed.",
            })
        except UpstreamUnavailable:
            return self._send(503, {"ok": False, "bridge": "black-house", "model_ready": False, "error": "Ollama is unavailable; start the configured model service"})

    def _read_json(self) -> dict:
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("transfer encoding is not supported")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if not 0 < length <= MAX_BODY:
            raise ValueError(f"request body must be between 1 and {MAX_BODY} bytes")
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError, RecursionError) as exc:
            raise ValueError("invalid JSON request") from exc

    def do_POST(self):
        if not self._authorize():
            return
        if urlsplit(self.path).path != "/api/chat":
            return self._send(404, {"error": "not found"})
        try:
            payload = _chat_payload(self.server.config, self._read_json())
            project = self.headers.get("X-Doug-Project", "")
            if project and not PROJECT_RE.fullmatch(project):
                raise ValueError("invalid project scope")
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        key = hashlib.sha256(json.dumps([project, payload], sort_keys=True, separators=(",", ":")).encode()).hexdigest() if project else ""
        if key:
            cached = self.server.cache.get(key)
            if cached is not None:
                return self._send(200, {**cached, "cached": True}, cache="hit")
        if not self.server.capacity.acquire(blocking=False):
            return self._send(429, {"error": "the local model is busy; retry after the running request completes"})
        try:
            result = _upstream(self.server.config, "/api/chat", payload)
            message = result.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
                raise UpstreamUnavailable("model returned no text content")
            if result.get("done") is not True:
                raise UpstreamUnavailable("model generation did not finish")
            result["bridge"] = "black-house"
            if key:
                self.server.cache.put(key, result)
            return self._send(200, {**result, "cached": False}, cache="miss" if key else "disabled")
        except UpstreamUnavailable as exc:
            return self._send(503, {"error": str(exc)})
        finally:
            self.server.capacity.release()


def main() -> None:
    try:
        config = BridgeConfig.from_env()
        server = BridgeServer(config)
    except (ValueError, OSError):
        raise SystemExit("Bridge configuration or bind failed; check DOUG_BRIDGE_* settings.") from None
    print(f"Black House bridge listening on port {server.server_port}; {len(config.origins)} browser origin(s) allowed.")
    print("Local model compute is required. GET /health checks model availability.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
