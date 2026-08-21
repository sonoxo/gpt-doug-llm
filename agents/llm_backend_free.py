"""Backward-compatible free-mode facade over the provider architecture."""

from __future__ import annotations

import os

from agents import llm_backend as _backend

PAID_MODE = os.environ.get("PAID_MODE", "false").lower() == "true"
FREE_ONLY = not PAID_MODE
DEFAULT_MODEL = _backend.DEFAULT_MODEL
USING_BACKEND = _backend.health()["backend"]
USING_FREE = _backend.health().get("free") is not False


def health():
    status = _backend.health()
    status.update({"paid_mode": PAID_MODE, "free": USING_FREE})
    return status


def chat_once(messages, model=None, options=None):
    if _backend.health()["backend"] == "openai" and not PAID_MODE:
        return {
            "message": {"role": "assistant", "content": "OpenAI is blocked unless PAID_MODE=true is explicitly set."},
            "done": True,
            "error": "paid_provider_blocked",
        }
    result = _backend.chat_once(messages, model, options)
    if result.get("error") == "provider_not_configured":
        message = result.setdefault("message", {"role": "assistant", "content": ""})
        content = str(message.get("content") or "").strip()
        if "offline workspace mode" not in content:
            message["content"] = (
                content
                + " offline workspace mode remains available for local inspection and planning."
            ).strip()
    return result


def stream_chat(messages, model=None, options=None):
    for event in _backend.chat_stream(messages, model, options):
        token = event.get("message", {}).get("content", "")
        if token:
            yield token


chat_stream = _backend.chat_stream
