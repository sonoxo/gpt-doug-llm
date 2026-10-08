from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .atomic import stack_manifest
from .config import SwarmConfig
from .models import utc_now
from .policy import CapabilityPolicy


@dataclass(frozen=True, slots=True)
class Heartbeat:
    status: str
    service: str
    version: str
    timestamp: str
    pid: int
    python: str
    agent_capacity: int
    adapter: str
    capability_profile: str
    enabled_capabilities: int
    atomic_stack_valid: bool
    atomic_layer_count: int
    endpoint: dict | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _package_version() -> str:
    try:
        return version("shaggoth-swarm-gpt100")
    except PackageNotFoundError:
        return "dev"


def probe_endpoint(endpoint: str, timeout: float = 3.0) -> dict:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("heartbeat endpoint must be an http(s) URL")

    started = time.monotonic()
    request = Request(
        endpoint,
        method="GET",
        headers={"User-Agent": f"shaggoth-heartbeat/{_package_version()}"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(1024)
            return {
                "url": endpoint,
                "ok": 200 <= getattr(response, "status", 200) < 400,
                "status_code": getattr(response, "status", 200),
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            }
    except HTTPError as exc:
        return {
            "url": endpoint,
            "ok": False,
            "status_code": exc.code,
            "error": str(exc),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "url": endpoint,
            "ok": False,
            "error": str(exc),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        }


def build_heartbeat(endpoint: str | None = None, timeout: float = 3.0) -> Heartbeat:
    config = SwarmConfig()
    policy = CapabilityPolicy.from_env()
    manifest = stack_manifest()
    endpoint_result = probe_endpoint(endpoint, timeout=timeout) if endpoint else None

    status = "alive"
    if not manifest["valid"]:
        status = "degraded"
    if endpoint_result is not None and not endpoint_result["ok"]:
        status = "degraded"

    return Heartbeat(
        status=status,
        service="shaggoth-swarm-gpt100",
        version=_package_version(),
        timestamp=utc_now(),
        pid=os.getpid(),
        python=platform.python_version(),
        agent_capacity=config.agent_count,
        adapter=config.adapter,
        capability_profile=os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
        enabled_capabilities=len(policy.allowed),
        atomic_stack_valid=manifest["valid"],
        atomic_layer_count=manifest["layer_count"],
        endpoint=endpoint_result,
    )


def format_heartbeat(heartbeat: Heartbeat) -> str:
    endpoint = ""
    if heartbeat.endpoint:
        endpoint = (
            f" endpoint={'up' if heartbeat.endpoint['ok'] else 'down'}"
            f" latency_ms={heartbeat.endpoint.get('elapsed_ms')}"
        )
    return (
        f"SHAGGOTH HEARTBEAT {heartbeat.status.upper()} | "
        f"agents={heartbeat.agent_capacity} "
        f"layers={heartbeat.atomic_layer_count} "
        f"stack={'ok' if heartbeat.atomic_stack_valid else 'invalid'} "
        f"profile={heartbeat.capability_profile} "
        f"adapter={heartbeat.adapter}"
        f"{endpoint}"
    )


def heartbeat_json(heartbeat: Heartbeat) -> str:
    return json.dumps(heartbeat.as_dict(), indent=2)
