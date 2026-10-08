from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


_RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
_SERVICE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_endpoints(raw: str) -> tuple[str, ...]:
    values = tuple(x.strip() for x in raw.split(",") if x.strip())
    if len(values) > 32:
        raise ValueError("at most 32 authorized endpoints are supported")
    return values


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    return parsed.scheme, parsed.hostname or "", parsed.port


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
    service_name: str = "shaggoth-swarm-gpt100"
    service_version: str = "0.2.0"
    bearer_token: str | None = None
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if len(self.endpoints) > 32:
            raise ValueError("at most 32 authorized endpoints are supported")
        for endpoint in self.endpoints:
            _validate_endpoint(endpoint)
        if self.interval_seconds < 5:
            raise ValueError("connect interval must be at least 5 seconds")
        if not 1 <= self.timeout_seconds <= 60:
            raise ValueError("connect timeout must be between 1 and 60 seconds")
        if not 1024 <= self.max_response_bytes <= 1048576:
            raise ValueError("max response bytes must be between 1024 and 1048576")
        if not _SERVICE_TOKEN.fullmatch(self.service_name):
            raise ValueError("service_name must be a visible service token up to 64 characters")
        if not _SERVICE_TOKEN.fullmatch(self.service_version):
            raise ValueError("service_version must be a visible version token up to 64 characters")
        if self.bearer_token is not None:
            if not self.bearer_token or len(self.bearer_token) > 8192:
                raise ValueError("bearer token length is invalid")
            if "\n" in self.bearer_token or "\r" in self.bearer_token:
                raise ValueError("bearer token contains invalid control characters")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        if not 0.25 <= self.retry_backoff_seconds <= 30:
            raise ValueError("retry_backoff_seconds must be between 0.25 and 30")

    @classmethod
    def from_env(cls) -> "ConnectorConfig":
        return cls(
            endpoints=_split_endpoints(os.getenv("SHAGGOTH_AUTHORIZED_ENDPOINTS", "")),
            interval_seconds=float(os.getenv("SHAGGOTH_CONNECT_INTERVAL_SECONDS", "30")),
            timeout_seconds=float(os.getenv("SHAGGOTH_CONNECT_TIMEOUT_SECONDS", "10")),
            max_response_bytes=int(os.getenv("SHAGGOTH_CONNECT_MAX_BYTES", "65536")),
            service_name=os.getenv("SHAGGOTH_SERVICE_NAME", "shaggoth-swarm-gpt100"),
            service_version=os.getenv("SHAGGOTH_SERVICE_VERSION", "0.2.0"),
            bearer_token=os.getenv("SHAGGOTH_CONNECT_BEARER_TOKEN") or None,
            max_retries=int(os.getenv("SHAGGOTH_CONNECT_MAX_RETRIES", "2")),
            retry_backoff_seconds=float(os.getenv("SHAGGOTH_CONNECT_RETRY_BACKOFF_SECONDS", "1")),
        )


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed: frozenset[str], source_url: str) -> None:
        super().__init__()
        self.allowed = allowed
        self.source_origin = _origin(source_url)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl not in self.allowed:
            raise HTTPError(newurl, code, "redirect target is not allowlisted", headers, fp)
        if _origin(newurl) != self.source_origin:
            raise HTTPError(newurl, code, "cross-origin redirects are not allowed", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_headers(config: ConnectorConfig) -> dict[str, str]:
    headers = {
        "User-Agent": f"{config.service_name}/{config.service_version}",
        "Accept": "application/json, text/plain;q=0.9, */*;q=0.1",
        "X-Client-Service": config.service_name,
        "X-Request-ID": uuid4().hex,
    }
    if config.bearer_token:
        headers["Authorization"] = f"Bearer {config.bearer_token}"
    return headers


Probe = Callable[[str, ConnectorConfig, frozenset[str]], dict]


def probe_endpoint(url: str, config: ConnectorConfig, allowed: frozenset[str]) -> dict:
    last_error = "request failed"

    for attempt in range(config.max_retries + 1):
        headers = _request_headers(config)
        request_id = headers["X-Request-ID"]
        opener = build_opener(_AllowlistedRedirectHandler(allowed, url))
        request = Request(url, method="GET", headers=headers)
        started = time.monotonic()

        try:
            with opener.open(request, timeout=config.timeout_seconds) as response:
                body = response.read(config.max_response_bytes + 1)
                truncated = len(body) > config.max_response_bytes
                if truncated:
                    body = body[: config.max_response_bytes]
                return {
                    "event": "connector_probe",
                    "service": config.service_name,
                    "endpoint": url,
                    "request_id": request_id,
                    "ok": True,
                    "status": getattr(response, "status", 200),
                    "bytes": len(body),
                    "truncated": truncated,
                    "attempts": attempt + 1,
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
                    "checked_at": _utc_now(),
                }
        except HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
            retryable = exc.code in _RETRYABLE_HTTP_STATUS
        except (URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            retryable = True

        if retryable and attempt < config.max_retries:
            time.sleep(config.retry_backoff_seconds * (2**attempt))
            continue

        return {
            "event": "connector_probe",
            "service": config.service_name,
            "endpoint": url,
            "request_id": request_id,
            "ok": False,
            "error": last_error,
            "attempts": attempt + 1,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            "checked_at": _utc_now(),
        }

    raise RuntimeError(last_error)


class AuthorizedConnectorMonitor:
    def __init__(self, config: ConnectorConfig, probe: Probe = probe_endpoint) -> None:
        if not config.endpoints:
            raise ValueError("no authorized endpoints configured")
        self.config = config
        self.allowed = frozenset(config.endpoints)
        self.probe = probe

    def poll_once(self) -> list[dict]:
        return [self.probe(endpoint, self.config, self.allowed) for endpoint in self.config.endpoints]

    def run_forever(self) -> None:
        while True:
            for event in self.poll_once():
                print(json.dumps(event, sort_keys=True), flush=True)
            time.sleep(self.config.interval_seconds)
