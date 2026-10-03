"""Read-only status adapters for operator-configured ecosystem services."""
from __future__ import annotations

import json
import os
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

SERVICES = {
    "XUNIA_CHAIN": ("XUNIA_CHAIN_BASE_URL", "/health"),
    "GEOVISION": ("ZYRA_LIVE_BASE_URL", "/api/va3lm/geovision/status"),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def service_status(target: str) -> dict:
    variable, path = SERVICES[target]
    base = os.environ.get(variable, "").strip().rstrip("/")
    if not base:
        return {"accepted": False, "target": target, "executionState": "SERVICE_UNCONFIGURED", "requiredConfiguration": variable}
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        return {"accepted": False, "target": target, "executionState": "SERVICE_CONFIGURATION_INVALID"}
    # Endpoints are operator configuration, never a mission-supplied URL. No
    # redirects, proxy forwarding, arbitrary methods, or credential propagation.
    try:
        request = Request(base + path, headers={"Accept": "application/json"}, method="GET")
        with build_opener(NoRedirect(), ProxyHandler({})).open(request, timeout=3) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("response too large")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("response must be an object")
        if target == "XUNIA_CHAIN":
            if payload.get("ok") is not True or payload.get("chainId") != "xunia-main-v1" or type(payload.get("height")) is not int or payload["height"] < 0:
                raise ValueError("invalid chain health")
            summary = {key: payload[key] for key in ("ok", "chainId", "height")}
        else:
            if payload.get("mode") != "VA3LM" or not isinstance(payload.get("detector"), dict):
                raise ValueError("invalid geovision status")
            summary = {
                "mode": "VA3LM",
                "foundryConfigured": payload.get("foundryConfigured") is True,
                "detectorReachable": payload["detector"].get("reachable") is True,
            }
        return {"accepted": True, "target": target, "executionState": "STATUS_OBSERVED", "readOnly": True, "serviceReported": summary, "note": "Status response only; does not verify inference, deployment, or a chain transaction."}
    except Exception:
        return {"accepted": False, "target": target, "executionState": "SERVICE_UNAVAILABLE"}
