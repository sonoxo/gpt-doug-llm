"""
Environment guard — blocks paid APIs unless explicitly opted in.
Imported automatically at the top of the agent chain to prevent any
accidental paid API usage.

This file is imported by agents/agent_chain.py BEFORE any LLM call.
It overrides the backend selection to enforce free-only mode.
"""
import os
import sys

# ── FREE MODE ENFORCEMENT ─────────────────────────────────────────────────
# Block OpenAI unless PAID_MODE=true is EXPLICITLY set
if os.environ.get("PAID_MODE", "false").lower() != "true":
    # Remove any paid API keys from the environment for this process
    # so no module can accidentally use them
    _PAID_KEYS_TO_BLOCK = [
        "OPENAI_API_KEY",
    ]
    for key in _PAID_KEYS_TO_BLOCK:
        if key in os.environ:
            os.environ[f"_BLOCKED_{key}"] = os.environ[key]  # save for later
            del os.environ[key]  # remove so no module can use it
            print(f"🔒 FREE MODE: blocked {key} (set PAID_MODE=true to enable)", file=sys.stderr)

# Gemini free tier is allowed (15 req/min, no charge)
# Ollama is always allowed (local, free)
# OpenAI is BLOCKED by default

def is_free_mode() -> bool:
    return os.environ.get("PAID_MODE", "false").lower() != "true"

def get_blocked_keys() -> list:
    return [k.replace("_BLOCKED_", "") for k in os.environ if k.startswith("_BLOCKED_")]

def enable_paid_mode():
    """Explicitly enable paid APIs. Must be called deliberately."""
    for key in list(os.environ.keys()):
        if key.startswith("_BLOCKED_"):
            original = key.replace("_BLOCKED_", "")
            os.environ[original] = os.environ[key]
            del os.environ[key]
    os.environ["PAID_MODE"] = "true"
    print("⚠️  PAID MODE ENABLED — API calls will cost money", file=sys.stderr)
