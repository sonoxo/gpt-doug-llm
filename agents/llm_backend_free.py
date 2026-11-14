"""Backward-compatible CL1 free-only facade over the provider architecture."""

from __future__ import annotations

from agents import llm_backend as _backend

# Legacy PAID_MODE flags can no longer unlock billed inference.
PAID_MODE = False
FREE_ONLY = True
DEFAULT_MODEL = _backend.DEFAULT_MODEL
USING_BACKEND = _backend.health()["backend"]
USING_FREE = True


def health():
    status = _backend.health()
    status.update({"paid_mode": False, "free": True, "billing_policy": "CL1_FREE_ONLY"})
    return status


def chat_once(messages, model=None, options=None):
    result = _backend.chat_once(messages, model, options)
    if result.get("error") == "provider_not_configured":
        message = result.setdefault(
            "message",
            {"role": "assistant", "content": ""},
        )
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
