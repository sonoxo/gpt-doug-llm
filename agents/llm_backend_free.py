"""
FREE-ONLY LLM Backend — zero cost, zero API keys, zero cloud bills.

This module enforces that GPT Doug NEVER uses a paid API unless explicitly
opted in. The default is always free:

  1. Ollama (local, free, runs on your machine) — DEFAULT
  2. Gemini API free tier (Google, free) — if GEMINI_API_KEY set AND FREE_MODE=true
  3. OpenAI (paid) — BLOCKED unless PAID_MODE=true is explicitly set

Usage:
  from agents.llm_backend_free import chat_once, DEFAULT_MODEL, USING_FREE

  # This will ALWAYS use a free backend. No accidental charges.
  response = chat_once(messages, model=None, options={})
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

# ── FREE MODE ENFORCEMENT ─────────────────────────────────────────────────
# Default: FREE ONLY. No paid APIs. No accidental charges.
PAID_MODE = os.environ.get("PAID_MODE", "false").lower() == "true"
FREE_ONLY = not PAID_MODE

# Ollama (local, free, always available)
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = os.environ.get("GPT_DOUG_MODEL", "gpt-doug")

# Gemini free tier (Google, 15 req/min free)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_FREE_TIER = os.environ.get("FREE_MODE", "true").lower() == "true"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# OpenAI (PAID — blocked by default)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def _select_backend() -> str:
    """Select the LLM backend. Returns one of: ollama, gemini_free, openai_paid, none.

    ENFORCEMENT RULES:
      - Default: Ollama (free, local)
      - If GEMINI_API_KEY is set: use Gemini free tier (15 req/min, no charge)
      - If OPENAI_API_KEY is set AND PAID_MODE=true: use OpenAI (costs money)
      - If no backend available: return 'none' (fail safe, don't charge)
    """
    # Priority 1: Ollama (always free, always default)
    # Check if Ollama is running
    try:
        urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=2)
        return "ollama"
    except Exception:
        pass

    # Priority 2: Gemini free tier (if key set and FREE_MODE not disabled)
    if GEMINI_API_KEY and GEMINI_FREE_TIER:
        return "gemini_free"

    # Priority 3: OpenAI (ONLY if PAID_MODE explicitly enabled)
    if OPENAI_API_KEY and PAID_MODE:
        return "openai_paid"

    # Fallback: no backend (fail safe)
    return "none"


USING_BACKEND = _select_backend()
DEFAULT_MODEL = {
    "ollama": OLLAMA_MODEL,
    "gemini_free": GEMINI_MODEL,
    "openai_paid": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    "none": "none",
}[USING_BACKEND]

USING_FREE = USING_BACKEND in ("ollama", "gemini_free")


def health() -> dict:
    """Check backend health — never makes a paid call."""
    return {
        "backend": USING_BACKEND,
        "model": DEFAULT_MODEL,
        "free": USING_FREE,
        "paid_mode": PAID_MODE,
        "ollama_reachable": USING_BACKEND == "ollama",
        "gemini_free_tier": USING_BACKEND == "gemini_free",
        "openai_blocked": not PAID_MODE and bool(OPENAI_API_KEY),
        "message": "FREE MODE — no paid APIs will be used" if USING_FREE else
                   ("PAID MODE — OpenAI enabled (costs money)" if USING_BACKEND == "openai_paid" else
                    "NO BACKEND — set up Ollama or GEMINI_API_KEY"),
    }


def chat_once(messages: list, model: str | None = None, options: dict | None = None) -> dict:
    """Non-streaming chat call. Returns Ollama-shaped dict.

    GUARANTEED: This function will NEVER make a paid API call unless
    PAID_MODE=true is explicitly set in the environment.

    If no free backend is available, it returns a helpful error instead
    of silently falling back to a paid service.
    """
    options = options or {}
    used_model = model or DEFAULT_MODEL

    if USING_BACKEND == "ollama":
        body = json.dumps({"model": used_model, "messages": messages, "stream": False,
                           "options": {"temperature": options.get("temperature", 0.7)}}).encode()
        try:
            req = urllib.request.Request(OLLAMA_CHAT_URL, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            return {"message": {"role": "assistant", "content": f"Ollama error: {e}. Is 'ollama serve' running?"}, "done": True, "error": str(e)}

    elif USING_BACKEND == "gemini_free":
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]
        body = json.dumps({"contents": contents, "generationConfig": {"temperature": options.get("temperature", 0.7)}})
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        try:
            req = urllib.request.Request(url, body.encode(), {"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return {"message": {"role": "assistant", "content": text}, "done": True}
        except urllib.error.URLError as e:
            return {"message": {"role": "assistant", "content": f"Gemini free tier error: {e}"}, "done": True, "error": str(e)}

    elif USING_BACKEND == "openai_paid":
        # ONLY reachable if PAID_MODE=true — costs money
        body = json.dumps({"model": used_model, "messages": messages, "max_tokens": options.get("max_tokens", 8192)})
        try:
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions", body.encode(),
                                         {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"message": {"role": "assistant", "content": text}, "done": True}
        except urllib.error.URLError as e:
            return {"message": {"role": "assistant", "content": f"OpenAI error: {e}"}, "done": True, "error": str(e)}

    else:
        # No free backend available — fail safe, don't charge
        return {
            "message": {"role": "assistant", "content": "No free LLM backend available. Install Ollama (free) or set GEMINI_API_KEY (free tier). Do NOT set PAID_MODE=true unless you want to pay for OpenAI."},
            "done": True,
            "error": "no_free_backend"
        }


def stream_chat(messages: list, model: str | None = None, options: dict | None = None):
    """Streaming chat generator. Same free-only enforcement."""
    if USING_BACKEND == "ollama":
        body = json.dumps({"model": model or DEFAULT_MODEL, "messages": messages, "stream": True}).encode()
        try:
            req = urllib.request.Request(OLLAMA_CHAT_URL, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    event = json.loads(line)
                    token = event.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if event.get("done"):
                        return
        except Exception as e:
            yield f"Ollama error: {e}"
    else:
        # Fallback: non-streaming
        result = chat_once(messages, model, options)
        yield result.get("message", {}).get("content", "")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║         FREE-ONLY LLM BACKEND — ZERO COST GUARANTEED                    ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")
    h = health()
    for k, v in h.items():
        print(f"║  {k}: {v}")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print()
    print("To use Ollama (free):    ollama serve")
    print("To use Gemini (free):   export GEMINI_API_KEY=your-key")
    print("To enable OpenAI (PAID): export PAID_MODE=true && export OPENAI_API_KEY=your-key")
    print()
    print("Default: FREE ONLY. No accidental charges. No surprise bills.")
