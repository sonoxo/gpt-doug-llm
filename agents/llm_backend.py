"""LLM backend abstraction: local Ollama or OpenAI's API.

server.py's chat/SSE plumbing is written against Ollama's event shape
({"message": {"role", "content"}, "done": bool}), so both backends here
normalize to that same shape rather than forking the request-handling code.
Selection is automatic: if OPENAI_API_KEY is set, use OpenAI (needed for
any deploy target without a local Ollama daemon); otherwise use Ollama.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = os.environ.get("GPT_DOUG_MODEL", "gpt-doug")

USING_OPENAI = bool(OPENAI_API_KEY)
DEFAULT_MODEL = OPENAI_MODEL if USING_OPENAI else OLLAMA_MODEL


def health() -> dict:
    if USING_OPENAI:
        # No cheap "is the key valid" probe worth spending a request on —
        # report configured, not verified-reachable, and let an actual
        # chat call surface auth errors.
        return {
            "backend": "openai",
            "ollama_reachable": None,
            "model": OPENAI_MODEL,
            "model_available": True,
            "models": [OPENAI_MODEL],
        }
    ok = True
    model_names = []
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=3) as resp:
            tags = json.loads(resp.read())
            model_names = [m.get("name", "") for m in tags.get("models", [])]
    except Exception:
        ok = False
    return {
        "backend": "ollama",
        "ollama_reachable": ok,
        "model": OLLAMA_MODEL,
        "model_available": any(m.split(":")[0] == OLLAMA_MODEL.split(":")[0] for m in model_names),
        "models": model_names,
    }


def chat_once(messages: list, model: str | None, options: dict) -> dict:
    """Non-streaming call. Returns an Ollama-shaped dict."""
    if USING_OPENAI:
        return _openai_chat_once(messages, model or OPENAI_MODEL, options)
    return _ollama_chat_once(messages, model or OLLAMA_MODEL, options)


def chat_stream(messages: list, model: str | None, options: dict):
    """Streaming call. Yields Ollama-shaped event dicts, ending with done=True."""
    if USING_OPENAI:
        yield from _openai_chat_stream(messages, model or OPENAI_MODEL, options)
    else:
        yield from _ollama_chat_stream(messages, model or OLLAMA_MODEL, options)


# ---------- Ollama ----------

def _ollama_chat_once(messages, model, options) -> dict:
    body = json.dumps({"model": model, "messages": messages, "stream": False, "options": options}).encode()
    req = urllib.request.Request(OLLAMA_CHAT_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def _ollama_chat_stream(messages, model, options):
    body = json.dumps({"model": model, "messages": messages, "stream": True, "options": options}).encode()
    req = urllib.request.Request(OLLAMA_CHAT_URL, body, {"Content-Type": "application/json"})
    upstream = urllib.request.urlopen(req, timeout=600)
    try:
        for line in upstream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield event
            if event.get("done"):
                break
    finally:
        upstream.close()


# ---------- OpenAI ----------

def _openai_headers():
    return {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}


def _openai_chat_once(messages, model, options) -> dict:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": options.get("temperature", 0.7),
    }).encode()
    req = urllib.request.Request(OPENAI_CHAT_URL, body, _openai_headers())
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"]
    return {"model": model, "message": {"role": "assistant", "content": content}, "done": True}


def _openai_chat_stream(messages, model, options):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": options.get("temperature", 0.7),
        "stream": True,
    }).encode()
    req = urllib.request.Request(OPENAI_CHAT_URL, body, _openai_headers())
    try:
        upstream = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")
        yield {"error": f"OpenAI API error {err.code}: {detail[:300]}"}
        yield {"done": True}
        return
    try:
        for raw in upstream:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                yield {"done": True}
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if token:
                yield {"model": model, "message": {"role": "assistant", "content": token}, "done": False}
    finally:
        upstream.close()
