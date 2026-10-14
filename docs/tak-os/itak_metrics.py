"""Private read-only TAK Server aggregate metric bridge for an operator-owned TAK deployment.

This module is deliberately separate from the synthetic CoT simulator and public
Earth feeds. No credentials or operational records may enter public static assets.
Only the official admin-only, read-only network counters endpoint is queried.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import secrets
import ssl
import threading
import time
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

METRICS_PATH = "/actuator/custom-network-metrics"
FIELDS = ("numClients", "bytesRead", "bytesWritten", "numReads", "numWrites")
MAX_RESPONSE_BYTES = 32768
MAX_COUNTER = (1 << 63) - 1


class MetricsSourceError(Exception):
    """Safe error type: its message never contains network locations or credentials."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_settings(env):
    """Fail closed on missing or insecure config; never echo its values to callers."""
    url = str(env.get("TAK_METRICS_BASE_URL") or "").strip()
    cert = str(env.get("TAK_METRICS_CLIENT_CERT") or "").strip()
    key = str(env.get("TAK_METRICS_CLIENT_KEY") or "").strip()
    ca = str(env.get("TAK_METRICS_CA_CERT") or "").strip()
    view_token = str(env.get("TAK_METRICS_VIEW_TOKEN") or "")
    try:
        parsed = urlsplit(url)
        port = parsed.port
        host = parsed.hostname
    except ValueError:
        return None
    if (parsed.scheme != "https" or not host or port is None or port < 1
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        return None
    if not all((cert, key, ca)) or len(view_token) < 32 or len(view_token) > 256:
        return None
    return {
        "endpoint": url.rstrip("/") + METRICS_PATH,
        "cert": cert, "key": key, "ca": ca, "token": view_token,
    }


def decode_network_metrics(value):
    """Strictly select safe scalar aggregate counters; ignore UIDs, callsigns, etc."""
    if not isinstance(value, dict):
        raise MetricsSourceError("invalid_server_response")
    counters = {}
    for name in FIELDS:
        raw = value.get(name)
        if type(raw) is not int or raw < 0 or raw > MAX_COUNTER:
            raise MetricsSourceError("missing_or_invalid_counter")
        counters[name] = int(raw)
    return counters


def verified_network_request(settings):
    """mTLS and a configured CA; reject cross-host redirects and untrusted formats."""
    context = ssl.create_default_context(cafile=settings["ca"])
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=settings["cert"], keyfile=settings["key"])
    opener = build_opener(HTTPSHandler(context=context), NoRedirect())
    request = Request(
        settings["endpoint"],
        headers={"Accept": "application/json", "User-Agent": "GPT-Doug-TAK-Private-Metrics/1.0"},
        method="GET",
    )
    with opener.open(request, timeout=4.0) as response:
        if response.status != 200:
            raise MetricsSourceError("upstream_unavailable")
        mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if mime != "application/json":
            raise MetricsSourceError("upstream_not_json")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise MetricsSourceError("upstream_response_too_large")
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MetricsSourceError("upstream_invalid_json") from exc


class PrivateItakMetrics:
    """Server-wide metrics only. Native iTAK-specific telemetry is NOT available."""

    def __init__(self, env=None, transport=None, monotonic=None, wall_clock=None):
        self._settings = read_settings(dict(os.environ if env is None else env))
        self._transport = transport or verified_network_request
        self._monotonic = monotonic or time.monotonic
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
        self._lock = threading.Lock()
        self._previous = None
        self._last_attempt = None
        self._last_report = None
        self._last_sample_monotonic = None

    def configured(self):
        return self._settings is not None

    def capabilities(self):
        return {
            "schema": "gpt-doug.tak-private-metrics.v1",
            "mode": "private_gateway_read_only",
            "configured": self.configured(),
            "requiresViewerAuthorization": True,
            "nativeItakAccess": False,
            "itakClientCountSupported": False,
            "source": "TAK Server aggregate admin network metrics",
            "pollIntervalSeconds": 10,
            "sensitiveDataIncluded": False,
        }

    def authorized(self, authorization):
        if not self.configured() or not isinstance(authorization, str):
            return False
        if not authorization.startswith("Bearer ") or len(authorization) > 264:
            return False
        return secrets.compare_digest(authorization[7:], self._settings["token"])

    def sample(self):
        if not self.configured():
            return 503, {"status": "not_configured", "metrics": None}
        with self._lock:
            now = self._monotonic()
            if self._last_attempt is not None and 0 <= now - self._last_attempt < 4.0:
                if self._last_report is None:
                    return 502, {"status": "source_unavailable", "metrics": None}
                cached = dict(self._last_report)
                cached["sampleAgeSeconds"] = round(max(0, now - self._last_sample_monotonic), 2)
                return 200, cached
            self._last_attempt = now
            start = self._monotonic()
            try:
                counters = decode_network_metrics(self._transport(self._settings))
            except Exception:
                # Fail closed; no stale counters and no server URL/cert/error strings.
                self._last_report = None
                self._last_sample_monotonic = None
                self._previous = None
                return 502, {"status": "source_unavailable", "metrics": None}
            elapsed = max(0.0, self._monotonic() - start)
            rates = {"readsPerSecond": None, "writesPerSecond": None,
                     "bytesReceivedPerSecond": None, "bytesSentPerSecond": None}
            if self._previous is not None:
                previous_time, previous_counts = self._previous
                seconds = self._monotonic() - previous_time
                if 1.0 <= seconds <= 180.0:
                    for label, source in (
                        ("readsPerSecond", "numReads"), ("writesPerSecond", "numWrites"),
                        ("bytesReceivedPerSecond", "bytesRead"), ("bytesSentPerSecond", "bytesWritten"),
                    ):
                        delta = counters[source] - previous_counts[source]
                        if delta >= 0:
                            rates[label] = round(delta / seconds, 2)
            self._previous = (self._monotonic(), counters)
            report = {
                "schema": "gpt-doug.tak-private-metrics.v1",
                "status": "current",
                "sampledAtUtc": self._wall_clock(),
                "sampleAgeSeconds": 0,
                "source": "TAK Server /actuator/custom-network-metrics",
                "sourceScope": "aggregate_all_tak_clients",
                "clientTypesIdentified": False,
                "itakClients": None,
                "itakDeviceBattery": None,
                "itakDeviceGps": None,
                "metrics": counters,
                "rates": rates,
                "upstreamFetchDurationMs": round(elapsed * 1000, 1),
                "mTLSVerifiedByPrivateGateway": True,
            }
            self._last_report = report
            self._last_sample_monotonic = self._monotonic()
            return 200, dict(report)
