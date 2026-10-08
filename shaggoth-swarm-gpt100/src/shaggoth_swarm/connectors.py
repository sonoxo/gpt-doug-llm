from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_endpoints(raw: str) -> tuple[str, ...]:
    values = tuple(x.strip() for x in raw.split(",") if x.strip())
    if len(values) > 32:
        raise ValueError("at most 32 authorized endpoints are supported")
    return values


def _validate_endpoint(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid endpoint: {url}")
    if parsed.username or parsed.password:
        raise ValueError("credentials must not be embedded in endpoint URLs")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("non-local endpoints must use https")


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    endpoints: tuple[str, ...]
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    max_response_bytes: int = 65536

    @classmethod
    def from_env(cls) -> "ConnectorConfig":
        endpoints = _split_endpoints(os.getenv("SHAGGOTH_AUTHORIZED_ENDPOINTS", ""))
        interval = float(os.getenv("SHAGGOTH_CONNECT_INTERVAL_SECONDS", "30"))
        timeout = float(os.getenv("SHAGGOTH_CONNECT_TIMEOUT_SECONDS", "10"))
        max_bytes = int(os.getenv("SHAGGOTH_CONNECT_MAX_BYTES", "65536"))
        if interval < 5:
            raise ValueError("connect interval must be at least 5 seconds")
        if not 1 <= timeout <= 60:
            raise ValueError("connect timeout must be between 1 and 60 seconds")
        if not 1024 <= max_bytes <= 1048576:
            raise ValueError("max response bytes must be between 1024 and 1048576")
        for endpoint in endpoints:
            _validate_endpoint(endpoint)
        return cls(endpoints=endpoints, interval_seconds=interval, timeout_seconds=timeout, max_response_bytes=max_bytes)


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed: frozenset[str]) -> None:
        super().__init__()
        self.allowed = allowed

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl not in self.allowed:
            raise HTTPError(newurl, code, "redirect target is not allowlisted", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


Probe = Callable[[str, float, int, frozenset[str]], dict]


def probe_endpoint(url: str, timeout: float, max_bytes: int, allowed: frozenset[str]) -> dict:
    opener = build_opener(_AllowlistedRedirectHandler(allowed))
    request = Request(
        url,
        method="GET",
        headers={"User-Agent": "shaggoth-swarm-authorized-monitor/0.1"},
    )
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                body = body[:max_bytes]
                truncated = True
            else:
                truncated = False
            return {
                "endpoint": url,
                "ok": True,
                "status": getattr(response, "status", 200),
                "bytes": len(body),
                "truncated": truncated,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
                "checked_at": _utc_now(),
            }
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "endpoint": url,
            "ok": False,
            "error": str(exc),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            "checked_at": _utc_now(),
        }


class AuthorizedConnectorMonitor:
    def __init__(self, config: ConnectorConfig, probe: Probe = probe_endpoint) -> None:
        if not config.endpoints:
            raise ValueError("no authorized endpoints configured")
        self.config = config
        self.allowed = frozenset(config.endpoints)
        self.probe = probe

    def poll_once(self) -> list[dict]:
        return [
            self.probe(endpoint, self.config.timeout_seconds, self.config.max_response_bytes, self.allowed)
            for endpoint in self.config.endpoints
        ]

    def run_forever(self) -> None:
        while True:
            for event in self.poll_once():
                print(json.dumps(event, sort_keys=True), flush=True)
            time.sleep(self.config.interval_seconds)
