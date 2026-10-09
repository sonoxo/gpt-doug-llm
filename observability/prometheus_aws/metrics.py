"""Small, bounded-cardinality, thread-safe Prometheus text metric exporter.

No prompts, credentials, paths or arbitrary user supplied strings enter labels.
"""
from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from typing import DefaultDict, Tuple


_ALLOWED_ROUTES = frozenset(
    {
        "/health", "/metrics", "/knowledge/search", "/inspect",
        "/sentinel/scan", "/shield/check", "/shield/sterilize",
        "/review/pr", "/payment/create",
    }
)


class GatewayMetrics:
    """Tracks request totals and wall-clock handling duration by fixed labels."""

    def __init__(self) -> None:
        self._started = time.monotonic()
        self._lock = threading.Lock()
        self._requests: DefaultDict[Tuple[str, str, str], int] = defaultdict(int)
        self._durations: DefaultDict[Tuple[str, str, str], float] = defaultdict(float)

    def observe(self, method: str, path: str, status: int, seconds: float = 0.0) -> None:
        method = method if method in {"GET", "POST"} else "OTHER"
        route = path if path in _ALLOWED_ROUTES else "other"
        status = str(status) if isinstance(status, int) and 100 <= status <= 599 else "other"
        elapsed = float(seconds)
        if not math.isfinite(elapsed) or elapsed < 0:
            elapsed = 0.0
        key = method, route, status
        with self._lock:
            self._requests[key] += 1
            self._durations[key] += elapsed

    def render(self) -> str:
        with self._lock:
            requests = dict(self._requests)
            durations = dict(self._durations)
        uptime = max(0.0, time.monotonic() - self._started)
        lines = [
            "# HELP gpt_doug_api_uptime_seconds Process uptime in seconds.",
            "# TYPE gpt_doug_api_uptime_seconds gauge",
            f"gpt_doug_api_uptime_seconds {uptime:.6f}",
            "# HELP gpt_doug_api_requests_total Completed HTTP responses.",
            "# TYPE gpt_doug_api_requests_total counter",
        ]
        for (method, route, status), count in sorted(requests.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"gpt_doug_api_requests_total{{{labels}}} {count}")
        lines.extend([
            "# HELP gpt_doug_api_request_duration_seconds_sum Total time for HTTP responses.",
            "# TYPE gpt_doug_api_request_duration_seconds_sum counter",
        ])
        for (method, route, status), seconds in sorted(durations.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"gpt_doug_api_request_duration_seconds_sum{{{labels}}} {seconds:.6f}")
        return "\n".join(lines) + "\n"
