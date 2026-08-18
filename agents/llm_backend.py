"""Provider-neutral chat facade for every GPT Doug surface.

Providers are explicitly selectable with ``GPT_DOUG_PROVIDER``. Supported
values are ``none``, ``openai``, ``claude``/``anthropic``, ``gemini``,
``ollama``, and ``auto``. ``auto`` tries configured providers in the order in
``GPT_DOUG_PROVIDER_ORDER`` (default: claude,openai,gemini,ollama) and falls
back when a provider is unavailable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator

Message = dict[str, str]
Event = dict


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
            "message": "Provider ready" if self.config.configured else "No AI provider configured",
        }

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
        self.config = ProviderConfig("openai", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), bool(self.api_key), False)

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
        if not self.api_key:
            return _configuration_error("OPENAI_API_KEY")
        with urllib.request.urlopen(self._request(messages, model, options, False), timeout=120) as response:
            data = json.loads(response.read())
        return {"model": model or self.config.model, "message": data["choices"][0]["message"], "done": True, "provider": "openai"}

    def chat_stream(self, messages, model, options):
        if not self.api_key:
            yield _configuration_error("OPENAI_API_KEY")
            return
        with urllib.request.urlopen(self._request(messages, model, options, True), timeout=120) as response:
            for raw in response:
                line = raw.decode(errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    yield {"done": True, "provider": "openai"}
                    return
                try:
                    token = json.loads(payload).get("choices", [{}])[0].get("delta", {}).get("content", "")
                except json.JSONDecodeError:
                    continue
                if token:
                    yield {"message": {"role": "assistant", "content": token}, "done": False, "provider": "openai"}


class AnthropicProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.config = ProviderConfig("claude", model, bool(self.api_key), False)

    def chat_once(self, messages, model, options):
        if not self.api_key:
            return _configuration_error("ANTHROPIC_API_KEY")
        used_model = model or self.config.model
        system = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
        chat_messages = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages if m.get("role") in {"user", "assistant"}
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
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read())
        content = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return {"model": used_model, "message": {"role": "assistant", "content": content}, "done": True, "provider": "claude"}


class GeminiProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.config = ProviderConfig("gemini", model, bool(self.api_key), True)

    def chat_once(self, messages, model, options):
        if not self.api_key:
            return _configuration_error("GEMINI_API_KEY")
        used_model = model or self.config.model
        contents = [{
            "role": "model" if item.get("role") == "assistant" else "user",
            "parts": [{"text": item.get("content", "")}],
        } for item in messages if item.get("role") != "system"]
        system = "\n\n".join(item.get("content", "") for item in messages if item.get("role") == "system")
        body = {"contents": contents, "generationConfig": {"temperature": options.get("temperature", 0.7)}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{used_model}:generateContent",
            json.dumps(body).encode(),
            {"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read())
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts)
        return {"model": used_model, "message": {"role": "assistant", "content": content}, "done": True, "provider": "gemini"}


class OllamaProvider(Provider):
    def __init__(self):
        model = os.environ.get("OLLAMA_MODEL", os.environ.get("GPT_DOUG_MODEL", "gpt-doug"))
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.config = ProviderConfig("ollama", model, True, True)

    def chat_once(self, messages, model, options):
        body = json.dumps({"model": model or self.config.model, "messages": messages, "stream": False, "options": options}).encode()
        request = urllib.request.Request(f"{self.base_url}/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read())
        data["provider"] = "ollama"
        return data

    def chat_stream(self, messages, model, options):
        body = json.dumps({"model": model or self.config.model, "messages": messages, "stream": True, "options": options}).encode()
        request = urllib.request.Request(f"{self.base_url}/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=600) as response:
            for raw in response:
                if not raw.strip():
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event["provider"] = "ollama"
                yield event
                if event.get("done"):
                    return


class AutoProvider(Provider):
    def __init__(self):
        requested = os.environ.get("GPT_DOUG_PROVIDER_ORDER", "claude,openai,gemini,ollama")
        self.order = [item.strip().lower() for item in requested.split(",") if item.strip()]
        self.providers = [_make_provider(name) for name in self.order if name not in {"none", "auto"}]
        configured = any(p.config.configured for p in self.providers)
        self.config = ProviderConfig("auto", "router", configured, None)

    def health(self):
        states = [p.health() for p in self.providers]
        return {
            "backend": "auto",
            "provider": "auto",
            "configured": any(s["configured"] for s in states),
            "model": "router",
            "model_available": any(s["configured"] for s in states),
            "models": [s["model"] for s in states if s.get("model")],
            "providers": states,
            "order": self.order,
            "free": None,
            "message": "Multi-provider router ready" if any(s["configured"] for s in states) else "No AI provider configured",
        }

    def chat_once(self, messages, model, options):
        errors = []
        for provider in self.providers:
            if not provider.config.configured:
                continue
            try:
                result = provider.chat_once(messages, model, options)
                if not result.get("error"):
                    result["routed_by"] = "auto"
                    return result
                errors.append(f"{provider.config.name}: {result.get('error')}")
            except (OSError, ValueError, KeyError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                errors.append(f"{provider.config.name}: {exc}")
        return {
            "message": {"role": "assistant", "content": "All configured AI providers failed."},
            "done": True,
            "error": "all_providers_failed",
            "provider_errors": errors,
        }

    def chat_stream(self, messages, model, options):
        result = self.chat_once(messages, model, options)
        yield result


def _configuration_error(variable: str) -> Event:
    return {
        "message": {"role": "assistant", "content": f"The selected provider is not configured. Set {variable} or choose another provider."},
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
    return [
        {"id": "none", "label": "Offline workspace", "configured": True},
        {"id": "auto", "label": "Auto router", "configured": any((os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("OPENAI_API_KEY"), os.environ.get("GEMINI_API_KEY"))) or True},
        {"id": "claude", "label": "Anthropic Claude", "configured": bool(os.environ.get("ANTHROPIC_API_KEY"))},
        {"id": "openai", "label": "OpenAI", "configured": bool(os.environ.get("OPENAI_API_KEY"))},
        {"id": "gemini", "label": "Google Gemini", "configured": bool(os.environ.get("GEMINI_API_KEY"))},
        {"id": "ollama", "label": "Ollama (local)", "configured": True},
    ]
