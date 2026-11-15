"""CL1 local-model admission and bounded inference resource policy.

The runtime never pulls models automatically and never routes to remote
inference. A request can select only an installed, non-cloud Ollama model.
Pure validation helpers intentionally make no network or filesystem calls.
"""
from __future__ import annotations

import math
import re
from typing import Any, Iterable

from agents.cl1_free_policy import is_local_ollama_model

_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?$")
_MAX_MODEL_LENGTH = 128

_DEFAULT_OPTIONS = {"num_ctx": 4096, "num_predict": 1024, "temperature": 0.7}
_INTEGER_BOUNDS = {
    "num_ctx": (256, 8192),
    "num_predict": (1, 2048),
    "top_k": (1, 100),
    "seed": (0, 2147483647),
}
_FLOAT_BOUNDS = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "repeat_penalty": (0.5, 2.0),
}
_MAX_STOPS = 8
_MAX_STOP_LENGTH = 80


def resolve_installed_model(requested: str, available: Iterable[str]) -> str | None:
    """Resolve a model *already present* in Ollama; never trigger pull/fallback.

    An omitted tag may resolve only to an installed :latest, never to an
    arbitrary installed size/quantization. Requested explicit tags must match.
    """
    if not isinstance(requested, str):
        return None
    name = requested.strip()
    if (
        not name or len(name) > _MAX_MODEL_LENGTH
        or not is_local_ollama_model(name)
        or not _MODEL_NAME.fullmatch(name)
    ):
        return None
    installed = {
        item for item in available
        if isinstance(item, str) and is_local_ollama_model(item)
    }
    if name in installed:
        return name
    if ":" not in name and name + ":latest" in installed:
        return name + ":latest"
    return None


def bounded_ollama_options(options: dict[str, Any] | None) -> dict[str, Any]:
    """Permit only known low-risk inference knobs and bounded resource usage.

    Unknown fields are never forwarded to Ollama. Known fields with invalid
    values reject the request rather than silently expand resource limits.
    """
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ValueError("invalid_inference_options")
    normalized: dict[str, Any] = dict(_DEFAULT_OPTIONS)
    if "max_tokens" in options and "num_predict" not in options:
        options = {**options, "num_predict": options["max_tokens"]}
    for key, (low, high) in _INTEGER_BOUNDS.items():
        if key not in options:
            continue
        value = options[key]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError("invalid_inference_options")
        normalized[key] = value
    for key, (low, high) in _FLOAT_BOUNDS.items():
        if key not in options:
            continue
        value = options[key]
        if (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not low <= value <= high
        ):
            raise ValueError("invalid_inference_options")
        normalized[key] = float(value)
    if "stop" in options:
        stops = options["stop"]
        if not isinstance(stops, list) or len(stops) > _MAX_STOPS:
            raise ValueError("invalid_inference_options")
        if any(not isinstance(s, str) or not s or len(s) > _MAX_STOP_LENGTH for s in stops):
            raise ValueError("invalid_inference_options")
        normalized["stop"] = list(stops)
    return normalized


def architecture_status() -> dict[str, object]:
    """Pure declarative snapshot; no network or sensitive environment values."""
    return {
        "schema": "cl1/llm-runtime-v2",
        "mode": "LOCAL_ONLY",
        "providers": ["ollama"],
        "remote_inference_allowed": False,
        "auto_model_pull_allowed": False,
        "redirects_allowed": False,
        "proxies_allowed": False,
        "max_context_tokens": _INTEGER_BOUNDS["num_ctx"][1],
        "max_output_tokens": _INTEGER_BOUNDS["num_predict"][1],
        "default_options": dict(_DEFAULT_OPTIONS),
        "paid_api_keys_required": False,
        "autonomous_execution": False,
    }
