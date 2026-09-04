#!/usr/bin/env python3
"""WorldMonitor convergence adapter for The Green House / Black House.

This module intentionally uses WorldMonitor's documented MCP-only
``get_signal_convergence`` tool instead of inventing a direct REST upstream.
It exposes a small local compatibility surface matching the Black House shape:

    GET /v1/intelligence/convergence?region=MENA&time_window=6h

The WorldMonitor API key is read from the environment and is never returned in
responses or accepted through query parameters.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

MCP_URL = os.getenv("WORLDMONITOR_MCP_URL", "https://worldmonitor.app/mcp")
SOURCE_WINDOW = "24h"
DEFAULT_MIN_DOMAINS = 3
REGION_CONFIG = Path(__file__).resolve().parents[1] / "config" / "worldmonitor-regions.json"


class WorldMonitorError(RuntimeError):
    """Raised when the upstream MCP request or response contract fails."""


@dataclass(frozen=True)
class RegionBounds:
    name: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    description: str = ""

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


def _api_key(explicit: str | None = None) -> str:
    key = explicit or os.getenv("WORLDMONITOR_API_KEY") or os.getenv("WM_API_KEY")
    if not key:
        raise WorldMonitorError(
            "WorldMonitor API key missing; set WORLDMONITOR_API_KEY (preferred) or WM_API_KEY"
        )
    return key


def load_regions(path: Path = REGION_CONFIG) -> dict[str, RegionBounds]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions: dict[str, RegionBounds] = {}
    for raw in payload.get("regions", []):
        name = str(raw["name"]).upper()
        bounds = raw["bounds"]
        regions[name] = RegionBounds(
            name=name,
            min_lat=float(bounds["minLat"]),
            max_lat=float(bounds["maxLat"]),
            min_lon=float(bounds["minLon"]),
            max_lon=float(bounds["maxLon"]),
            description=str(raw.get("description", "")),
        )
        for alias in raw.get("aliases", []):
            regions[str(alias).upper()] = regions[name]
    return regions


def build_mcp_request(api_key: str, min_domains: int = DEFAULT_MIN_DOMAINS) -> Request:
    min_domains = max(2, min(5, int(min_domains)))
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "black-house-worldmonitor-convergence",
            "method": "tools/call",
            "params": {
                "name": "get_signal_convergence",
                "arguments": {"min_domains": min_domains},
            },
        }
    ).encode("utf-8")
    return Request(
        MCP_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-WorldMonitor-Key": api_key,
            "User-Agent": "GPT-DOUG-LLM-Black-House/1.0",
        },
        method="POST",
    )


def _extract_mcp_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    if envelope.get("error"):
        raise WorldMonitorError(f"WorldMonitor MCP error: {envelope['error']}")

    result = envelope.get("result")
    if not isinstance(result, dict):
        raise WorldMonitorError("WorldMonitor MCP response missing result object")

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    if isinstance(result.get("data"), dict):
        return result

    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    raise WorldMonitorError("WorldMonitor MCP response contained no structured convergence payload")


def fetch_convergence(
    *,
    min_domains: int = DEFAULT_MIN_DOMAINS,
    api_key: str | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = build_mcp_request(_api_key(api_key), min_domains)
    try:
        with opener(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        raise WorldMonitorError(f"WorldMonitor HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise WorldMonitorError(f"WorldMonitor request failed: {error}") from error

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as error:
        raise WorldMonitorError("WorldMonitor returned invalid JSON") from error
    if not isinstance(envelope, dict):
        raise WorldMonitorError("WorldMonitor returned a non-object JSON envelope")
    return _extract_mcp_payload(envelope)


def _normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    score = alert.get("score")
    confidence = None
    if isinstance(score, (int, float)):
        confidence = round(max(0.0, min(100.0, float(score))) / 100.0, 4)

    return {
        "type": "multi_signal_convergence",
        "signals": list(alert.get("types") or []),
        "confidence": confidence,
        "confidence_basis": "normalized_from_worldmonitor_convergence_score_0_100",
        "score": score,
        "total_events": alert.get("totalEvents"),
        "cell_id": alert.get("cellId"),
        "location": {
            "lat": alert.get("lat"),
            "lng": alert.get("lon"),
            "name": alert.get("location"),
        },
    }


def adapt_response(
    upstream: dict[str, Any],
    *,
    region: str | None = None,
    time_window: str = SOURCE_WINDOW,
    regions: dict[str, RegionBounds] | None = None,
) -> dict[str, Any]:
    data = upstream.get("data") if isinstance(upstream.get("data"), dict) else {}
    alerts = data.get("alerts") if isinstance(data.get("alerts"), list) else []

    region_bounds: RegionBounds | None = None
    if region:
        regions = regions or load_regions()
        region_bounds = regions.get(region.upper())
        if region_bounds is None:
            raise WorldMonitorError(f"unsupported region alias: {region}")

    selected: list[dict[str, Any]] = []
    for raw in alerts:
        if not isinstance(raw, dict):
            continue
        lat, lon = raw.get("lat"), raw.get("lon")
        if region_bounds is not None:
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                continue
            if not region_bounds.contains(float(lat), float(lon)):
                continue
        selected.append(_normalize_alert(raw))

    requested = str(time_window or SOURCE_WINDOW).lower()
    window_exact = requested == SOURCE_WINDOW

    return {
        "status": "success",
        "data": selected,
        "meta": {
            "source": "WorldMonitor MCP/get_signal_convergence",
            "requested_region": region,
            "requested_time_window": requested,
            "source_time_window": SOURCE_WINDOW,
            "window_exact": window_exact,
            "window_note": (
                "Exact WorldMonitor convergence window."
                if window_exact
                else "WorldMonitor convergence is computed over a fixed 24h window; narrower/wider requests are compatibility metadata only."
            ),
            "stale": bool(upstream.get("stale", False)),
            "cached_at": upstream.get("cached_at"),
            "min_domains": data.get("min_domains"),
            "feeds": data.get("feeds", {}),
            "region_definition": region_bounds.description if region_bounds else None,
        },
    }


def query(
    *,
    region: str | None = None,
    time_window: str = SOURCE_WINDOW,
    min_domains: int = DEFAULT_MIN_DOMAINS,
    api_key: str | None = None,
) -> dict[str, Any]:
    upstream = fetch_convergence(min_domains=min_domains, api_key=api_key)
    return adapt_response(upstream, region=region, time_window=time_window)


class ConvergenceHandler(BaseHTTPRequestHandler):
    server_version = "BlackHouseWorldMonitor/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        parsed = urlparse(self.path)
        if parsed.path != "/v1/intelligence/convergence":
            self._json(HTTPStatus.NOT_FOUND, {"status": "error", "error": "not_found"})
            return

        params = parse_qs(parsed.query)
        region = (params.get("region") or [None])[0]
        time_window = (params.get("time_window") or [SOURCE_WINDOW])[0]
        try:
            min_domains = int((params.get("min_domains") or [DEFAULT_MIN_DOMAINS])[0])
            payload = query(region=region, time_window=time_window, min_domains=min_domains)
        except (ValueError, WorldMonitorError) as error:
            self._json(HTTPStatus.BAD_GATEWAY, {"status": "error", "error": str(error)})
            return
        self._json(HTTPStatus.OK, payload)

    def log_message(self, format: str, *args: Any) -> None:
        # Never log credentials; query parameters contain no key by design.
        super().log_message(format, *args)


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise WorldMonitorError("compatibility gateway is loopback-only by design")
    server = ThreadingHTTPServer((host, port), ConvergenceHandler)
    print(f"WorldMonitor convergence gateway: http://{host}:{port}/v1/intelligence/convergence")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Black House WorldMonitor convergence adapter")
    parser.add_argument("--region", default=None)
    parser.add_argument("--time-window", default=SOURCE_WINDOW)
    parser.add_argument("--min-domains", type=int, default=DEFAULT_MIN_DOMAINS)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    try:
        if args.serve:
            serve(args.host, args.port)
            return 0
        print(
            json.dumps(
                query(region=args.region, time_window=args.time_window, min_domains=args.min_domains),
                indent=2,
            )
        )
        return 0
    except KeyboardInterrupt:
        return 130
    except WorldMonitorError as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
