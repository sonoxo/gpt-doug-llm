#!/usr/bin/env python3
"""GPT-DOUG OSIRIS Safe Mirror.

Continuously mirrors a strictly allowlisted set of public, non-tactical OSIRIS
API layers into a local snapshot for Cesium/WebGL visualization.

This worker never uses credentials, never probes hosts, never accesses OSIRIS
recon/scanner endpoints, and never commandeers remote or third-party GPU/CPU.
GPU acceleration belongs to the local renderer (Cesium/WebGL), not the mirror.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

SAFE_ROUTES: dict[str, int] = {
    "health": 30,
    "earthquakes": 60,
    "fires": 180,
    "weather": 300,
    "air-quality": 300,
    "space-weather": 300,
    "news": 180,
    "live-news": 180,
    "gdelt": 300,
    "markets": 300,
}

BLOCKED_ROUTES = {
    "flights", "cctv", "conflicts", "frontlines", "maritime", "radar",
    "scanner", "osint", "malware", "cyber-threats", "infrastructure",
    "region-dossier", "telegram-feed", "sentinel", "crypto", "satellites",
}

DEFAULT_BASE = "http://127.0.0.1:3000"
DEFAULT_OUT = Path.home() / ".local" / "share" / "gpt-doug" / "osiris-mirror"

_STOP = False


def _stop(*_: Any) -> None:
    global _STOP
    _STOP = True


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


@dataclass
class LayerState:
    route: str
    ok: bool
    fetched_at: float
    latency_ms: int
    sha256: str | None
    bytes: int
    error: str | None = None


def _atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _safe_routes_from_env() -> list[str]:
    raw = os.getenv("OSIRIS_MIRROR_ROUTES", "").strip()
    if not raw:
        return list(SAFE_ROUTES)
    requested = [x.strip() for x in raw.split(",") if x.strip()]
    blocked = sorted(set(requested) & BLOCKED_ROUTES)
    unknown = sorted(set(requested) - set(SAFE_ROUTES) - BLOCKED_ROUTES)
    if blocked:
        raise SystemExit("Blocked OSIRIS routes requested: " + ", ".join(blocked))
    if unknown:
        raise SystemExit("Unknown/non-allowlisted routes requested: " + ", ".join(unknown))
    return requested


def _validate_base_url(base_url: str) -> str:
    p = urllib.parse.urlparse(base_url)
    if p.scheme not in {"http", "https"} or not p.netloc:
        raise SystemExit("OSIRIS_BASE_URL must be an http(s) URL")
    return base_url.rstrip("/")


def fetch_json(base_url: str, route: str, max_bytes: int, timeout: float) -> tuple[Any, LayerState]:
    if route not in SAFE_ROUTES:
        raise ValueError(f"Route not allowlisted: {route}")
    url = f"{base_url}/api/{urllib.parse.quote(route, safe='')}"
    started = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "GPT-DOUG-OSIRIS-SAFE-MIRROR/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "json" not in content_type:
                raise ValueError(f"unexpected content type: {content_type or 'unknown'}")
            raw = resp.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError(f"response exceeded {max_bytes} byte limit")
        obj = json.loads(raw.decode("utf-8"))
        digest = hashlib.sha256(raw).hexdigest()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return obj, LayerState(route, True, time.time(), latency_ms, digest, len(raw))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, LayerState(route, False, time.time(), latency_ms, None, 0, str(exc)[:500])


def build_snapshot(base_url: str, routes: list[str], out_dir: Path, max_bytes: int, timeout: float) -> dict[str, Any]:
    previous: dict[str, Any] = {}
    snapshot_path = out_dir / "snapshot.json"
    if snapshot_path.exists():
        try:
            previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            previous = {}

    layers: dict[str, Any] = {}
    states: dict[str, Any] = {}
    for route in routes:
        data, state = fetch_json(base_url, route, max_bytes, timeout)
        if state.ok:
            layers[route] = data
        else:
            old_layers = previous.get("layers", {}) if isinstance(previous, dict) else {}
            if route in old_layers:
                layers[route] = old_layers[route]
        states[route] = asdict(state)

    now = time.time()
    healthy = sum(1 for v in states.values() if v["ok"])
    snapshot = {
        "schema": "gpt-doug.osiris-safe-mirror.v1",
        "generated_at": now,
        "source": {
            "name": "OSIRIS",
            "base_url": base_url,
            "mode": "authorized-public-safe-mirror",
        },
        "render": {
            "gpu_mode": "local-webgl-only",
            "note": "Cesium/WebGL may use the operator's local GPU. The mirror never borrows or commandeers third-party compute.",
        },
        "policy": {
            "allowlisted_routes": routes,
            "blocked_routes": sorted(BLOCKED_ROUTES),
        },
        "health": {
            "healthy_layers": healthy,
            "total_layers": len(routes),
            "status": "ONLINE" if healthy == len(routes) else ("DEGRADED" if healthy else "OFFLINE"),
        },
        "layers": layers,
        "layer_state": states,
    }
    _atomic_write(snapshot_path, snapshot)
    _atomic_write(out_dir / "status.json", {k: snapshot[k] for k in ("generated_at", "source", "render", "health", "layer_state")})
    return snapshot


def run_daemon(base_url: str, routes: list[str], out_dir: Path, max_bytes: int, timeout: float, min_interval: int) -> int:
    due = {r: 0.0 for r in routes}
    while not _STOP:
        now = time.monotonic()
        active = [r for r in routes if due[r] <= now]
        if active:
            build_snapshot(base_url, active, out_dir, max_bytes, timeout)
            now2 = time.monotonic()
            for r in active:
                due[r] = now2 + max(min_interval, SAFE_ROUTES[r])
        sleep_for = min([max(0.5, due[r] - time.monotonic()) for r in routes] or [1.0])
        time.sleep(min(sleep_for, 5.0))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Mirror safe public OSIRIS layers into GPT-DOUG")
    p.add_argument("--once", action="store_true", help="refresh once and exit")
    p.add_argument("--base-url", default=os.getenv("OSIRIS_BASE_URL", DEFAULT_BASE))
    p.add_argument("--out", default=os.getenv("OSIRIS_MIRROR_OUT", str(DEFAULT_OUT)))
    p.add_argument("--max-bytes", type=int, default=int(os.getenv("OSIRIS_MIRROR_MAX_BYTES", "5000000")))
    p.add_argument("--timeout", type=float, default=float(os.getenv("OSIRIS_MIRROR_TIMEOUT", "10")))
    p.add_argument("--min-interval", type=int, default=int(os.getenv("OSIRIS_MIRROR_MIN_INTERVAL", "30")))
    args = p.parse_args()

    if not (65536 <= args.max_bytes <= 20_000_000):
        raise SystemExit("--max-bytes must be between 65536 and 20000000")
    if not (1 <= args.timeout <= 60):
        raise SystemExit("--timeout must be between 1 and 60 seconds")
    if not (15 <= args.min_interval <= 3600):
        raise SystemExit("--min-interval must be between 15 and 3600 seconds")

    base_url = _validate_base_url(args.base_url)
    routes = _safe_routes_from_env()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.once:
        snap = build_snapshot(base_url, routes, out_dir, args.max_bytes, args.timeout)
        print(json.dumps(snap["health"], sort_keys=True))
        return 0 if snap["health"]["healthy_layers"] else 2
    return run_daemon(base_url, routes, out_dir, args.max_bytes, args.timeout, args.min_interval)


if __name__ == "__main__":
    sys.exit(main())
