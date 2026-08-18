"""Provider-neutral chat facade for GPT Doug.

Supported providers: none, openai, claude/anthropic, gemini, ollama, auto.
The auto router only uses providers that pass readiness checks. Requests are
protected by bounded retries and per-provider circuit breakers so repeated
failures cannot create infinite failover loops.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator

Message = dict[str, str]
Event = dict

DEFAULT_TIMEOUT = float(os.environ.get("GPT_DOUG_PROVIDER_TIMEOUT", "120"))
MAX_RETRIES = max(0, min(int(os.environ.get("GPT_DOUG_MAX_RETRIES", "1")), 3))
CB_FAILURE_THRESHOLD = max(1, int(os.environ.get("GPT_DOUG_CB_FAILURE_THRESHOLD", "3")))
CB_COOLDOWN_S = max(5.0, float(os.environ.get("GPT_DOUG_CB_COOLDOWN", "30")))
PLACEHOLDERS = {"", "...", "***", "changeme", "change-me", "your_real_key", "your-api-key", "test"}


def _valid_secret(value: str) -> bool:
    value = (value or "").strip()
    return value.lower() not in PLACEHOLDERS and len(value) >= 12


def _safe_provider_error(name: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{name}: HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"{name}: network unavailable"
    if isinstance(exc, TimeoutError):
        return f"{name}: timeout"
    return f"{name}: provider failure"


@dataclass
class CircuitState:
    failures: int = 0
    state: str = "closed"  # closed | open | half_open
    opened_at: float = 0.0
    last_error: str = ""


class CircuitBreaker:
    def __init__(self, threshold: int = CB_FAILURE_THRESHOLD, cooldown_s: float = CB_COOLDOWN_S):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._lock = threading.Lock()
        self._states: dict[str, CircuitState] = {}

    def _get(self, name: str) -> CircuitState:
        return self._states.setdefault(name, CircuitState())

    def allow(self, name: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._get(name)
            if state.state == "closed":
                return True
            if state.state == "open" and now - state.opened_at >= self.cooldown_s:
                state.state = "half_open"
                return True
            return state.state == "half_open"

    def success(self, name: str) -> None:
        with self._lock:
            state = self._get(name)
            state.failures = 0
            state.state = "closed"
            state.opened_at = 0.0
            state.last_error = ""

    def failure(self, name: str, reason: str) -> None:
        with self._lock:
            state = self._get(name)
            state.failures += 1
            state.last_error = reason
            if state.state == "half_open" or state.failures >= self.threshold:
                state.state = "open"
                state.opened_at = time.monotonic()

    def status(self, name: str) -> dict:
        with self._lock:
            state = self._get(name)
            remaining = 0.0
            if state.state == "open":
                remaining = max(0.0, self.cooldown_s - (time.monotonic() - state.opened_at))
            return {
                "state": state.state,
                "failures": state.failures,
                "cooldown_remaining_s": round(remaining, 1),
                "last_error": state.last_error,
            }


_circuits = CircuitBreaker()


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    configured: bool
    free: bool | None


class Provider:
    config: ProviderConfig

    def health(self) -> dict:
        result = {
            "backend": self.config.name,
            "provider": self.config.name,
            "configured": self.config.configured,
            "model": self.config.model,
            "model_available": self.config.configured,
            "models": [self.config.model] if self.config.model else [],
            "free": self.config.free,
            "message": "Provider ready" if self.config.configured else "Provider not configured",
        }
        result["circuit"] = _circuits.status(self.config.name)
        return result

    def ready(self) -> bool:
        state = self.health()
        return bool(state.get("configured") and state.get("model_available") and _circuits.allow(self.config.name))

    def chat_once(self, messages: list[Message], model: str | None, options: dict) -> Event:
        raise NotImplementedError

    def chat_stream(self, messages: list[Message], model: str | None, options: dict) -> Iterator[Event]:
        yield self.chat_once(messages, model, options)


class NoProvider(Provider):
    config = ProviderConfig("none", "", False, True)

    def chat_once(self, messages, model, options):
        return {"message": {"role": "assistant", "content": "No AI provider is configured."}, "done": True, "offline": True, "error": "provider_not_configured"}


class OpenAIProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.config = ProviderConfig("openai", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), _valid_secret(self.api_key), False)

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("OPENAI_API_KEY")
        body = json.dumps({"model": model or self.config.model, "messages": messages, "temperature": options.get("temperature", 0.7)}).encode()
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", body, {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
        return {"model": model or self.config.model, "message": data["choices"][0]["message"], "done": True, "provider": "openai"}


class AnthropicProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.config = ProviderConfig("claude", os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"), _valid_secret(self.api_key), False)

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("ANTHROPIC_API_KEY")
        used_model = model or self.config.model
        system = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
        body = {"model": used_model, "max_tokens": int(options.get("max_tokens", 4096)), "temperature": options.get("temperature", 0.7), "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages if m.get("role") in {"user", "assistant"}]}
        if system:
            body["system"] = system
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(), {"content-type": "application/json", "x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
        content = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return {"model": used_model, "message": {"role": "assistant", "content": content}, "done": True, "provider": "claude"}


class GeminiProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.config = ProviderConfig("gemini", os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), _valid_secret(self.api_key), True)

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("GEMINI_API_KEY")
        used_model = model or self.config.model
        contents = [{"role": "model" if m.get("role") == "assistant" else "user", "parts": [{"text": m.get("content", "")}]} for m in messages if m.get("role") != "system"]
        body = {"contents": contents, "generationConfig": {"temperature": options.get("temperature", 0.7)}}
        system = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{used_model}:generateContent", json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
        content = "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        return {"model": used_model, "message": {"role": "assistant", "content": content}, "done": True, "provider": "gemini"}


class OllamaProvider(Provider):
    def __init__(self):
        model = os.environ.get("OLLAMA_MODEL", os.environ.get("GPT_DOUG_MODEL", "gpt-doug"))
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.config = ProviderConfig("ollama", model, True, True)

    def health(self) -> dict:
        models, reachable = [], False
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.base_url}/api/tags", headers={"Accept": "application/json"}), timeout=3) as response:
                data = json.loads(response.read())
            models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
            reachable = True
        except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
            pass
        wanted = self.config.model
        available = reachable and any(name == wanted or name.startswith(wanted + ":") for name in models)
        return {"backend": "ollama", "provider": "ollama", "configured": reachable, "model": wanted, "model_available": available, "models": models, "free": True, "message": "Provider ready" if available else ("Ollama reachable; requested model missing" if reachable else "Ollama not reachable"), "circuit": _circuits.status("ollama")}

    def chat_once(self, messages, model, options):
        state = self.health()
        if not state["configured"]:
            return {"message": {"role": "assistant", "content": "Ollama is not reachable."}, "done": True, "error": "provider_unreachable"}
        used_model = model or self.config.model
        if used_model == self.config.model and not state["model_available"]:
            return {"message": {"role": "assistant", "content": "Configured Ollama model is not installed."}, "done": True, "error": "model_unavailable"}
        body = json.dumps({"model": used_model, "messages": messages, "stream": False, "options": options}).encode()
        with urllib.request.urlopen(urllib.request.Request(f"{self.base_url}/api/chat", body, {"Content-Type": "application/json"}), timeout=max(DEFAULT_TIMEOUT, 600)) as response:
            data = json.loads(response.read())
        data["provider"] = "ollama"
        return data


class AutoProvider(Provider):
    def __init__(self):
        requested = os.environ.get("GPT_DOUG_PROVIDER_ORDER", "claude,openai,gemini,ollama")
        self.order = [item.strip().lower() for item in requested.split(",") if item.strip()]
        self.providers = [_make_provider(name) for name in self.order if name not in {"none", "auto"}]
        self.config = ProviderConfig("auto", "router", True, None)

    def health(self):
        states = [p.health() for p in self.providers]
        ready = [s for s in states if s.get("configured") and s.get("model_available") and s.get("circuit", {}).get("state") != "open"]
        return {"backend": "auto", "provider": "auto", "configured": bool(ready), "model": "router", "model_available": bool(ready), "models": [s["model"] for s in ready if s.get("model")], "providers": states, "order": self.order, "free": None, "message": "Multi-provider router ready" if ready else "No provider passed readiness/circuit checks"}

    def chat_once(self, messages, model, options):
        errors = []
        for provider in self.providers:
            name = provider.config.name
            state = provider.health()
            if not (state.get("configured") and state.get("model_available")):
                errors.append(f"{name}: not ready")
                continue
            if not _circuits.allow(name):
                errors.append(f"{name}: circuit open")
                continue
            for attempt in range(MAX_RETRIES + 1):
                try:
                    result = provider.chat_once(messages, model, options)
                    if not result.get("error"):
                        _circuits.success(name)
                        result["routed_by"] = "auto"
                        result["attempt"] = attempt + 1
                        return result
                    reason = str(result.get("error"))[:80]
                    _circuits.failure(name, reason)
                    errors.append(f"{name}: {reason}")
                    if not _circuits.allow(name):
                        break
                except Exception as exc:
                    reason = _safe_provider_error(name, exc)
                    _circuits.failure(name, reason)
                    errors.append(reason)
                    if not _circuits.allow(name):
                        break
        return {"message": {"role": "assistant", "content": "All configured AI providers failed readiness, retry, or circuit-breaker checks."}, "done": True, "error": "all_providers_failed", "provider_errors": errors, "circuits": {p.config.name: _circuits.status(p.config.name) for p in self.providers}}


def _configuration_error(variable: str) -> Event:
    return {"message": {"role": "assistant", "content": f"The selected provider is not configured with a valid credential. Set {variable} or choose another provider."}, "done": True, "error": "provider_not_configured"}


PROVIDER_FACTORIES = {"none": NoProvider, "openai": OpenAIProvider, "claude": AnthropicProvider, "anthropic": AnthropicProvider, "gemini": GeminiProvider, "ollama": OllamaProvider}


def _make_provider(name: str) -> Provider:
    factory = PROVIDER_FACTORIES.get(name)
    return factory() if factory else NoProvider()


def _load_provider() -> Provider:
    name = os.environ.get("GPT_DOUG_PROVIDER", "none").strip().lower() or "none"
    return AutoProvider() if name == "auto" else _make_provider(name)


_provider = _load_provider()
DEFAULT_MODEL = _provider.config.model


def health() -> dict:
    return _provider.health()


def chat_once(messages: list[Message], model: str | None = None, options: dict | None = None) -> Event:
    return _provider.chat_once(messages, model, options or {})


def chat_stream(messages: list[Message], model: str | None = None, options: dict | None = None):
    yield from _provider.chat_stream(messages, model, options or {})


def available_providers() -> list[dict]:
    providers = [AnthropicProvider(), OpenAIProvider(), GeminiProvider(), OllamaProvider()]
    return [
        {"id": "none", "label": "Offline workspace", "configured": True},
        {"id": "auto", "label": "Auto router", "configured": any(p.ready() for p in providers)},
        {"id": "claude", "label": "Anthropic Claude", "configured": providers[0].ready()},
        {"id": "openai", "label": "OpenAI", "configured": providers[1].ready()},
        {"id": "gemini", "label": "Google Gemini", "configured": providers[2].ready()},
        {"id": "ollama", "label": "Ollama (local)", "configured": providers[3].ready()},
    ]
