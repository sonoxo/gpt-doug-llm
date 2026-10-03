"""Qwen provider gateway for GPT-Doug.

Supports Alibaba Cloud Model Studio's OpenAI-compatible endpoint and local
OpenAI-compatible Qwen servers (for example vLLM or SGLang on loopback).
Network access is opt-in: a remote endpoint requires QWEN_API_KEY or
DASHSCOPE_API_KEY. Local loopback HTTP may run without a key.

Scale-out mode is enabled by QWEN_BASE_URLS, a comma-separated list of
OpenAI-compatible replicas. Requests are distributed across the least-loaded
healthy replicas with bounded per-replica concurrency and failover.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_REMOTE_BASE_URL = "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
DEFAULT_REMOTE_MODEL = "qwen3.7-plus"
DEFAULT_LOCAL_MODEL = "Qwen/Qwen3.8-Flash-Next"
DEFAULT_TIMEOUT = float(os.getenv("GPT_DOUG_PROVIDER_TIMEOUT", "120"))
DEFAULT_MAX_INFLIGHT = 4
DEFAULT_RETRIES = 1
DEFAULT_COOLDOWN = 10.0

PLACEHOLDERS = {
    "",
    "...",
    "***",
    "changeme",
    "change-me",
    "your_real_key",
    "your-api-key",
    "test",
}

_POOL_LOCK = threading.Lock()
_POOL_INFLIGHT: dict[str, int] = {}
_POOL_BLOCKED_UNTIL: dict[str, float] = {}
_POOL_CURSOR = 0


def _valid_secret(value: str) -> bool:
    value = (value or "").strip()
    return value.lower() not in PLACEHOLDERS and len(value) >= 12


def _is_loopback(base_url: str) -> bool:
    parsed = urllib.parse.urlparse(base_url)
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme == "https" and host:
        return base_url.rstrip("/")

    if parsed.scheme == "http" and _is_loopback(base_url):
        return base_url.rstrip("/")

    raise ValueError("Qwen base URL must use HTTPS, except loopback HTTP is allowed")


def _bounded_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _bounded_float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def max_inflight_per_replica() -> int:
    return _bounded_int_env("GPT_DOUG_PROVIDER_MAX_INFLIGHT", DEFAULT_MAX_INFLIGHT, 1, 64)


def provider_retries() -> int:
    return _bounded_int_env("GPT_DOUG_PROVIDER_RETRIES", DEFAULT_RETRIES, 0, 8)


def provider_cooldown() -> float:
    return _bounded_float_env("GPT_DOUG_PROVIDER_COOLDOWN", DEFAULT_COOLDOWN, 0.0, 300.0)


def api_key() -> str:
    return (
        os.getenv("QWEN_API_KEY", "").strip()
        or os.getenv("DASHSCOPE_API_KEY", "").strip()
    )


def base_urls() -> list[str]:
    configured_pool = os.getenv("QWEN_BASE_URLS", "").strip()
    if configured_pool:
        raw_urls = [item.strip() for item in configured_pool.split(",") if item.strip()]
    else:
        raw_urls = [
            os.getenv("QWEN_BASE_URL", DEFAULT_REMOTE_BASE_URL).strip()
            or DEFAULT_REMOTE_BASE_URL
        ]

    urls: list[str] = []
    seen: set[str] = set()
    for raw_url in raw_urls:
        endpoint = _validate_base_url(raw_url)
        if endpoint not in seen:
            seen.add(endpoint)
            urls.append(endpoint)

    if not urls:
        raise ValueError("at least one Qwen base URL is required")
    return urls


def base_url() -> str:
    return base_urls()[0]


def default_model() -> str:
    configured = os.getenv("QWEN_MODEL", "").strip()
    if configured:
        return configured
    endpoints = base_urls()
    key_ready = _valid_secret(api_key())
    usable = [endpoint for endpoint in endpoints if _is_loopback(endpoint) or key_ready]
    return DEFAULT_LOCAL_MODEL if usable and all(_is_loopback(endpoint) for endpoint in usable) else DEFAULT_REMOTE_MODEL


DEFAULT_MODEL = os.getenv("QWEN_MODEL", "").strip() or DEFAULT_REMOTE_MODEL


def _usable_endpoints(endpoints: list[str]) -> list[str]:
    key_ready = _valid_secret(api_key())
    return [endpoint for endpoint in endpoints if _is_loopback(endpoint) or key_ready]


def health() -> dict:
    try:
        endpoints = base_urls()
    except ValueError as exc:
        return {
            "backend": "qwen",
            "provider": "qwen",
            "configured": False,
            "model": os.getenv("QWEN_MODEL", "").strip() or DEFAULT_REMOTE_MODEL,
            "model_available": False,
            "free": None,
            "message": str(exc),
        }

    usable = _usable_endpoints(endpoints)
    key_ready = _valid_secret(api_key())
    model = default_model()
    local_only = all(_is_loopback(endpoint) for endpoint in usable) if usable else False

    return {
        "backend": "qwen",
        "provider": "qwen",
        "configured": bool(usable),
        "model": model,
        "model_available": bool(usable) and bool(model),
        "models": [model] if model else [],
        "base_url": usable[0] if usable else endpoints[0],
        "base_urls": usable,
        "replicas": len(usable),
        "max_inflight_per_replica": max_inflight_per_replica(),
        "local": local_only,
        "free": True if local_only else None,
        "message": (
            f"Qwen replica pool ready ({len(usable)} local replica{'s' if len(usable) != 1 else ''})"
            if local_only
            else (
                f"Qwen Model Studio gateway configured ({len(usable)} replica{'s' if len(usable) != 1 else ''})"
                if key_ready and usable
                else "Set QWEN_API_KEY or DASHSCOPE_API_KEY to enable remote Qwen"
            )
        ),
    }


def _reset_pool_state() -> None:
    """Clear process-local scheduling state. Primarily useful for deterministic tests."""
    global _POOL_CURSOR
    with _POOL_LOCK:
        _POOL_INFLIGHT.clear()
        _POOL_BLOCKED_UNTIL.clear()
        _POOL_CURSOR = 0


def _acquire_endpoint(endpoints: list[str], exclude: set[str] | None = None) -> str | None:
    global _POOL_CURSOR
    excluded = exclude or set()
    now = time.monotonic()
    max_inflight = max_inflight_per_replica()

    with _POOL_LOCK:
        eligible = [endpoint for endpoint in endpoints if endpoint not in excluded]
        if not eligible:
            return None

        start = _POOL_CURSOR % len(eligible)
        rotated = eligible[start:] + eligible[:start]
        _POOL_CURSOR += 1

        healthy = [
            endpoint
            for endpoint in rotated
            if _POOL_BLOCKED_UNTIL.get(endpoint, 0.0) <= now
        ]
        candidates = healthy or rotated
        candidates.sort(key=lambda endpoint: _POOL_INFLIGHT.get(endpoint, 0))

        for endpoint in candidates:
            inflight = _POOL_INFLIGHT.get(endpoint, 0)
            if inflight < max_inflight:
                _POOL_INFLIGHT[endpoint] = inflight + 1
                return endpoint

    return None


def _release_endpoint(endpoint: str, *, failed: bool = False) -> None:
    with _POOL_LOCK:
        _POOL_INFLIGHT[endpoint] = max(0, _POOL_INFLIGHT.get(endpoint, 1) - 1)
        if failed:
            _POOL_BLOCKED_UNTIL[endpoint] = time.monotonic() + provider_cooldown()
        else:
            _POOL_BLOCKED_UNTIL.pop(endpoint, None)


def _request_for(endpoint: str, used_model: str, messages: list[dict[str, str]], options: dict) -> urllib.request.Request:
    body = {
        "model": used_model,
        "messages": messages,
        "temperature": options.get("temperature", 0.2),
        "stream": False,
    }

    max_tokens = options.get("max_tokens")
    if max_tokens is not None:
        body["max_tokens"] = int(max_tokens)

    headers = {"Content-Type": "application/json"}
    key = api_key()
    if _valid_secret(key):
        headers["Authorization"] = f"Bearer {key}"

    return urllib.request.Request(
        f"{endpoint}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )


def chat_once(
    messages: list[dict[str, str]],
    model: str | None = None,
    options: dict | None = None,
) -> dict:
    options = options or {}
    state = health()
    if not state["configured"]:
        return {
            "message": {
                "role": "assistant",
                "content": state["message"],
            },
            "done": True,
            "provider": "qwen",
            "error": "provider_not_configured",
        }

    endpoints = list(state["base_urls"])
    used_model = model or state["model"]
    tried: set[str] = set()
    attempts = min(len(endpoints), 1 + provider_retries())
    last_error = "provider_unavailable"

    for _ in range(attempts):
        endpoint = _acquire_endpoint(endpoints, tried)
        if endpoint is None:
            last_error = "provider_busy" if not tried else last_error
            break
        tried.add(endpoint)
        request = _request_for(endpoint, used_model, messages, options)

        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:  # nosec B310 -- URL validated above
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            retryable = exc.code in {408, 425, 429} or exc.code >= 500
            _release_endpoint(endpoint, failed=retryable)
            last_error = f"http_{exc.code}"
            if retryable:
                continue
            return {
                "message": {"role": "assistant", "content": f"Qwen HTTP {exc.code}"},
                "done": True,
                "provider": "qwen",
                "error": last_error,
                "endpoint": endpoint,
            }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            _release_endpoint(endpoint, failed=True)
            last_error = "provider_unavailable"
            continue

        choices = data.get("choices") or []
        if not choices:
            _release_endpoint(endpoint, failed=True)
            last_error = "empty_response"
            continue

        _release_endpoint(endpoint, failed=False)
        message = choices[0].get("message") or {}
        return {
            "model": used_model,
            "message": {
                "role": message.get("role", "assistant"),
                "content": message.get("content", ""),
            },
            "done": True,
            "provider": "qwen",
            "endpoint": endpoint,
        }

    content = "Qwen provider busy" if last_error == "provider_busy" else "Qwen provider unavailable"
    return {
        "message": {"role": "assistant", "content": content},
        "done": True,
        "provider": "qwen",
        "error": last_error,
    }
