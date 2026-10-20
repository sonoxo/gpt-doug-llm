"""Provider-neutral, fail-closed pre-inference and pre-tool-execution adapter."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, TypeVar

T = TypeVar("T")


class GateDenied(PermissionError):
    """Operation must not proceed without an authorized watchtower verdict."""


class WatchtowerClient:
    def __init__(self, model_token: str, url: str = "http://127.0.0.1:8877"):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password or parsed.path.strip("/"):
            raise ValueError("base URL must be an http(s) origin without embedded credentials")
        if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("HTTP allowed only on loopback; remote deployments require HTTPS")
        if not model_token or len(model_token) < 24:
            raise ValueError("a private per-model ingest token is required")
        self.url = url.rstrip("/")
        self.token = model_token

    def require(self, event: dict) -> dict:
        """Ask the gateway to permit the exact event before execution, or raise."""
        request = urllib.request.Request(self.url + "/api/v1/evaluate", method="POST",
            data=json.dumps(event).encode("utf-8"), headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            })
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                result = json.load(response)
                if response.status != 200 or result.get("verdict") != "allow" or result.get("enforce") is not True:
                    raise GateDenied("watchtower policy did not grant execution")
                return result
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            raise GateDenied("watchtower unavailable or denied execution (fail closed)") from exc

    def execute(self, event: dict, callback: Callable[[], T]) -> T:
        """Wrap an arbitrary provider/tool callback. Callback is never reached on denial."""
        self.require(event)
        return callback()


def otel_observation(attributes: dict, *, agent_id: str, trace_id: str = "") -> dict:
    """Normalize a minimal OpenTelemetry GenAI span to this gateway's contract.

    Event content is intentionally not collected. Register the model with
    telemetry:observe first; this doesn't stand in for guarding tool use.
    """
    if not isinstance(attributes, dict):
        raise ValueError("OpenTelemetry attributes must be an object")
    return {
        "model_id": str(attributes.get("gen_ai.request.model") or attributes.get("gen_ai.response.model") or "unknown-model"),
        "provider": str(attributes.get("gen_ai.system") or "other"),
        "agent_id": agent_id, "trace_id": trace_id,
        "kind": "telemetry", "action": "observe", "scope": "public",
        "resource": "otel:gen-ai-span", "content": "",
        "estimated_tokens": int(attributes.get("gen_ai.usage.input_tokens") or 0) + int(attributes.get("gen_ai.usage.output_tokens") or 0),
    }
