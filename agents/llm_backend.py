"""Provider-neutral chat facade for GPT Doug / GPT XUNIA.

Supported providers: none, openai, claude/anthropic, gemini, ollama, auto,
and xunia. ``auto`` routes to the first ready provider. ``xunia`` fans out
to all ready providers, then uses one ready provider as an arbiter to stream a
single consensus answer.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterator

from agents.ai_action_plan import inject_policy

Message = dict[str, str]
Event = dict

DEFAULT_TIMEOUT = float(os.environ.get("GPT_DOUG_PROVIDER_TIMEOUT", "120"))
PLACEHOLDERS = {"", "...", "***", "changeme", "change-me", "your_real_key", "your-api-key", "test"}


def _valid_secret(value: str) -> bool:
    value = (value or "").strip()
    if value.lower() in PLACEHOLDERS:
        return False
    if len(value) < 12:
        return False
    return True


def _safe_provider_error(name: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{name}: HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"{name}: network unavailable"
    if isinstance(exc, TimeoutError):
        return f"{name}: timeout"
    return f"{name}: provider failure"


def _safe_urlopen(
    request: urllib.request.Request,
    *,
    timeout: float,
    allow_local_http: bool = False,
):
    """Open a provider request only after validating its transport target.

    Remote providers must use HTTPS. Plain HTTP is permitted only for explicit
    loopback Ollama endpoints, preserving the local default without allowing a
    configurable provider URL to become a file/custom-scheme read primitive.
    """
    parsed = urllib.parse.urlparse(request.full_url)
    host = (parsed.hostname or "").lower()
    is_https = parsed.scheme == "https"
    is_loopback_http = (
        allow_local_http
        and parsed.scheme == "http"
        and host in {"127.0.0.1", "localhost", "::1"}
    )
    if not (is_https or is_loopback_http):
        raise ValueError(f"Refusing unsafe provider URL: {parsed.scheme}://{host}")
    return urllib.request.urlopen(request, timeout=timeout)  # nosec B310 -- scheme/host validated above


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    configured: bool
    free: bool | None


class Provider:
    config: ProviderConfig

    def health(self) -> dict:
        return {
            "backend": self.config.name,
            "provider": self.config.name,
            "configured": self.config.configured,
            "model": self.config.model,
            "model_available": self.config.configured,
            "models": [self.config.model] if self.config.model else [],
            "free": self.config.free,
            "message": "Provider ready" if self.config.configured else "Provider not configured",
        }

    def ready(self) -> bool:
        state = self.health()
        return bool(state.get("configured") and state.get("model_available"))

    def chat_once(self, messages: list[Message], model: str | None, options: dict) -> Event:
        raise NotImplementedError

    def chat_stream(self, messages: list[Message], model: str | None, options: dict) -> Iterator[Event]:
        yield self.chat_once(messages, model, options)


class NoProvider(Provider):
    config = ProviderConfig("none", "", False, True)

    def chat_once(self, messages, model, options):
        return {
            "message": {"role": "assistant", "content": "No AI provider is configured."},
            "done": True,
            "offline": True,
            "error": "provider_not_configured",
        }


class OpenAIProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.config = ProviderConfig(
            "openai",
            os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            _valid_secret(self.api_key),
            False,
        )

    def _request(self, messages, model, options, stream):
        body = json.dumps({
            "model": model or self.config.model,
            "messages": messages,
            "temperature": options.get("temperature", 0.7),
            "stream": stream,
        }).encode()
        return urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            body,
            {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("OPENAI_API_KEY")
        with _safe_urlopen(
            self._request(messages, model, options, False),
            timeout=DEFAULT_TIMEOUT,
        ) as response:
            data = json.loads(response.read())
        return {
            "model": model or self.config.model,
            "message": data["choices"][0]["message"],
            "done": True,
            "provider": "openai",
        }


class AnthropicProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.config = ProviderConfig("claude", model, _valid_secret(self.api_key), False)

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("ANTHROPIC_API_KEY")
        used_model = model or self.config.model
        system = "\n\n".join(
            m.get("content", "") for m in messages if m.get("role") == "system"
        )
        chat_messages = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages
            if m.get("role") in {"user", "assistant"}
        ]
        body = {
            "model": used_model,
            "max_tokens": int(options.get("max_tokens", 4096)),
            "temperature": options.get("temperature", 0.7),
            "messages": chat_messages,
        }
        if system:
            body["system"] = system
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            json.dumps(body).encode(),
            {
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with _safe_urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
        content = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        return {
            "model": used_model,
            "message": {"role": "assistant", "content": content},
            "done": True,
            "provider": "claude",
        }


class GeminiProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.config = ProviderConfig("gemini", model, _valid_secret(self.api_key), True)

    def chat_once(self, messages, model, options):
        if not self.config.configured:
            return _configuration_error("GEMINI_API_KEY")
        used_model = model or self.config.model
        contents = [{
            "role": "model" if item.get("role") == "assistant" else "user",
            "parts": [{"text": item.get("content", "")}],
        } for item in messages if item.get("role") != "system"]
        system = "\n\n".join(
            item.get("content", "") for item in messages if item.get("role") == "system"
        )
        body = {
            "contents": contents,
            "generationConfig": {"temperature": options.get("temperature", 0.7)},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{used_model}:generateContent",
            json.dumps(body).encode(),
            {"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        with _safe_urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts)
        return {
            "model": used_model,
            "message": {"role": "assistant", "content": content},
            "done": True,
            "provider": "gemini",
        }


class OllamaProvider(Provider):
    def __init__(self):
        model = os.environ.get("OLLAMA_MODEL", os.environ.get("GPT_DOUG_MODEL", "gpt-doug"))
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.config = ProviderConfig("ollama", model, True, True)

    def health(self) -> dict:
        models = []
        reachable = False
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"Accept": "application/json"},
            )
            with _safe_urlopen(request, timeout=3, allow_local_http=True) as response:
                data = json.loads(response.read())
            models = [
                item.get("name", "")
                for item in data.get("models", [])
                if item.get("name")
            ]
            reachable = True
        except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
            reachable = False
        wanted = self.config.model
        model_available = reachable and any(
            name == wanted or name.startswith(wanted + ":") for name in models
        )
        return {
            "backend": "ollama",
            "provider": "ollama",
            "configured": reachable,
            "model": wanted,
            "model_available": model_available,
            "models": models,
            "free": True,
            "message": (
                "Provider ready"
                if model_available
                else ("Ollama reachable; requested model missing" if reachable else "Ollama not reachable")
            ),
        }

    def chat_once(self, messages, model, options):
        state = self.health()
        if not state["configured"]:
            return {
                "message": {"role": "assistant", "content": "Ollama is not reachable."},
                "done": True,
                "error": "provider_unreachable",
            }
        used_model = model or self.config.model
        if used_model == self.config.model and not state["model_available"]:
            return {
                "message": {
                    "role": "assistant",
                    "content": "Configured Ollama model is not installed.",
                },
                "done": True,
                "error": "model_unavailable",
            }
        body = json.dumps({
            "model": used_model,
            "messages": messages,
            "stream": False,
            "options": options,
        }).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            body,
            {"Content-Type": "application/json"},
        )
        with _safe_urlopen(
            request,
            timeout=max(DEFAULT_TIMEOUT, 600),
            allow_local_http=True,
        ) as response:
            data = json.loads(response.read())
        data["provider"] = "ollama"
        return data


class AutoProvider(Provider):
    def __init__(self):
        requested = os.environ.get(
            "GPT_DOUG_PROVIDER_ORDER",
            "claude,openai,gemini,ollama",
        )
        self.order = [item.strip().lower() for item in requested.split(",") if item.strip()]
        self.providers = [
            _make_provider(name)
            for name in self.order
            if name not in {"none", "auto", "xunia"}
        ]
        self.config = ProviderConfig("auto", "router", True, None)

    def health(self):
        states = [p.health() for p in self.providers]
        ready_states = [
            state
            for state in states
            if state.get("configured") and state.get("model_available")
        ]
        return {
            "backend": "auto",
            "provider": "auto",
            "configured": bool(ready_states),
            "model": "router",
            "model_available": bool(ready_states),
            "models": [state["model"] for state in ready_states if state.get("model")],
            "providers": states,
            "order": self.order,
            "free": None,
            "message": (
                "Multi-provider router ready"
                if ready_states
                else "No provider passed readiness checks"
            ),
        }

    def chat_once(self, messages, model, options):
        errors = []
        for provider in self.providers:
            state = provider.health()
            if not (state.get("configured") and state.get("model_available")):
                errors.append(f"{provider.config.name}: not ready")
                continue
            try:
                result = provider.chat_once(messages, None, options)
                if not result.get("error"):
                    result["routed_by"] = "auto"
                    return result
                errors.append(f"{provider.config.name}: {result.get('error')}")
            except Exception as exc:
                errors.append(_safe_provider_error(provider.config.name, exc))
        return {
            "message": {
                "role": "assistant",
                "content": "All configured AI providers failed readiness or request checks.",
            },
            "done": True,
            "error": "all_providers_failed",
            "provider_errors": errors,
        }


class XuniaProvider(AutoProvider):
    """Fan-out + consensus provider for GPT XUNIA SUPER BRAIN 9000."""

    def __init__(self):
        super().__init__()
        self.config = ProviderConfig("xunia", "xunia-consensus", True, None)

    def health(self):
        state = super().health()
        ready = [
            item for item in state.get("providers", [])
            if item.get("configured") and item.get("model_available")
        ]
        return {
            **state,
            "backend": "xunia",
            "provider": "xunia",
            "model": "xunia-consensus",
            "models": ["xunia-consensus"],
            "configured": bool(ready),
            "model_available": bool(ready),
            "message": (
                f"GPT XUNIA ready with {len(ready)} provider(s)"
                if ready
                else "No provider passed GPT XUNIA readiness checks"
            ),
        }

    def chat_once(self, messages, model, options):
        from agents.xunia_stream import xunia_once
        return xunia_once(self, messages, options)


def _configuration_error(variable: str) -> Event:
    return {
        "message": {
            "role": "assistant",
            "content": (
                "The selected provider is not configured with a valid credential. "
                f"Set {variable} or choose another provider."
            ),
        },
        "done": True,
        "error": "provider_not_configured",
    }


PROVIDER_FACTORIES = {
    "none": NoProvider,
    "openai": OpenAIProvider,
    "claude": AnthropicProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def _make_provider(name: str) -> Provider:
    factory = PROVIDER_FACTORIES.get(name)
    return factory() if factory else NoProvider()


def _load_provider() -> Provider:
    name = os.environ.get("GPT_DOUG_PROVIDER", "none").strip().lower() or "none"
    if name == "xunia":
        return XuniaProvider()
    if name == "auto":
        return AutoProvider()
    return _make_provider(name)


_provider = _load_provider()
DEFAULT_MODEL = _provider.config.model


def health() -> dict:
    state = _provider.health()
    state["ai_action_plan_profile"] = os.environ.get("GPT_DOUG_AI_ACTION_PLAN", "1").strip().lower() not in {"0", "false", "off", "no", "disabled"}
    return state


def chat_once(
    messages: list[Message],
    model: str | None = None,
    options: dict | None = None,
) -> Event:
    return _provider.chat_once(inject_policy(messages), model, options or {})


def chat_stream(
    messages: list[Message],
    model: str | None = None,
    options: dict | None = None,
):
    from agents.xunia_stream import stream_auto, stream_provider, xunia_stream

    prepared = inject_policy(messages)
    opts = options or {}
    if isinstance(_provider, XuniaProvider):
        yield from xunia_stream(_provider, prepared, opts)
        return
    if isinstance(_provider, AutoProvider):
        yield from stream_auto(_provider, prepared, model, opts)
        return
    yield from stream_provider(_provider, prepared, model, opts)


def available_providers() -> list[dict]:
    providers = [AnthropicProvider(), OpenAIProvider(), GeminiProvider(), OllamaProvider()]
    ready = any(provider.ready() for provider in providers)
    return [
        {"id": "none", "label": "Offline workspace", "configured": True},
        {"id": "auto", "label": "Auto router", "configured": ready},
        {"id": "xunia", "label": "GPT XUNIA consensus", "configured": ready},
        {"id": "claude", "label": "Anthropic Claude", "configured": providers[0].ready()},
        {"id": "openai", "label": "OpenAI", "configured": providers[1].ready()},
        {"id": "gemini", "label": "Google Gemini", "configured": providers[2].ready()},
        {"id": "ollama", "label": "Ollama (local)", "configured": providers[3].ready()},
    ]
