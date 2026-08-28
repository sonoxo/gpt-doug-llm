"""Qwen provider gateway for GPT-Doug.

Supports Alibaba Cloud Model Studio's OpenAI-compatible endpoint and local
OpenAI-compatible Qwen servers (for example vLLM or SGLang on loopback).
Network access is opt-in: a remote endpoint requires QWEN_API_KEY or
DASHSCOPE_API_KEY. Local loopback HTTP may run without a key.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_REMOTE_BASE_URL = "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
DEFAULT_REMOTE_MODEL = "qwen3.7-plus"
DEFAULT_LOCAL_MODEL = "Qwen/Qwen3.8-Flash-Next"
DEFAULT_TIMEOUT = float(os.getenv("GPT_DOUG_PROVIDER_TIMEOUT", "120"))

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


def api_key() -> str:
    return (
        os.getenv("QWEN_API_KEY", "").strip()
        or os.getenv("DASHSCOPE_API_KEY", "").strip()
    )


def base_url() -> str:
    return _validate_base_url(
        os.getenv("QWEN_BASE_URL", DEFAULT_REMOTE_BASE_URL).strip()
        or DEFAULT_REMOTE_BASE_URL
    )


def default_model() -> str:
    configured = os.getenv("QWEN_MODEL", "").strip()
    if configured:
        return configured
    return DEFAULT_LOCAL_MODEL if _is_loopback(base_url()) else DEFAULT_REMOTE_MODEL


DEFAULT_MODEL = os.getenv("QWEN_MODEL", "").strip() or DEFAULT_REMOTE_MODEL


def health() -> dict:
    try:
        endpoint = base_url()
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

    local = _is_loopback(endpoint)
    key_ready = _valid_secret(api_key())
    configured = local or key_ready
    model = default_model()

    return {
        "backend": "qwen",
        "provider": "qwen",
        "configured": configured,
        "model": model,
        "model_available": configured and bool(model),
        "models": [model] if model else [],
        "base_url": endpoint,
        "local": local,
        "free": True if local else None,
        "message": (
            "Qwen local OpenAI-compatible gateway ready"
            if local
            else (
                "Qwen Model Studio gateway configured"
                if key_ready
                else "Set QWEN_API_KEY or DASHSCOPE_API_KEY to enable remote Qwen"
            )
        ),
    }


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

    endpoint = state["base_url"]
    used_model = model or state["model"]
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

    request = urllib.request.Request(
        f"{endpoint}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:  # nosec B310 -- URL validated above
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return {
            "message": {"role": "assistant", "content": f"Qwen HTTP {exc.code}"},
            "done": True,
            "provider": "qwen",
            "error": f"http_{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, OSError):
        return {
            "message": {"role": "assistant", "content": "Qwen provider unavailable"},
            "done": True,
            "provider": "qwen",
            "error": "provider_unavailable",
        }

    choices = data.get("choices") or []
    if not choices:
        return {
            "message": {"role": "assistant", "content": "Qwen returned no choices"},
            "done": True,
            "provider": "qwen",
            "error": "empty_response",
        }

    message = choices[0].get("message") or {}
    return {
        "model": used_model,
        "message": {
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
        },
        "done": True,
        "provider": "qwen",
    }
