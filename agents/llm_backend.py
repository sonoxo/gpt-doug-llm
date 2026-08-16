"""Provider-neutral chat facade for every GPT Doug surface.

The default provider is ``none``: the application remains usable without an
API key and importing this module never probes the network. Providers are
selected explicitly with ``GPT_DOUG_PROVIDER``. Ollama is retained only as an
opt-in compatibility provider and is never discovered or started implicitly.
"""

from __future__ import annotations

import json
import importlib.util
import platform
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
        result = self.chat_once(messages, model, options)
        yield result


class NoProvider(Provider):
    config = ProviderConfig("none", "", False, True)

    def chat_once(self, messages, model, options):
        content = (
            "GPT Doug is running in offline workspace mode. Chat generation is unavailable until "
            "an AI provider is explicitly configured, but projects, files, previews, memory, tools, "
            "agents, terminal features, and security controls remain available."
        )
        return {
            "message": {"role": "assistant", "content": content},
            "done": True,
            "offline": True,
            "error": "provider_not_configured",
        }


class OpenAIProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.config = ProviderConfig("openai", model, bool(self.api_key), False)

    def _request(self, messages, model, options, stream):
        body = json.dumps({
            "model": model or self.config.model,
            "messages": messages,
            "temperature": options.get("temperature", 0.7),
            "stream": stream,
        }).encode()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        return urllib.request.Request("https://api.openai.com/v1/chat/completions", body, headers)

    def chat_once(self, messages, model, options):
        if not self.api_key:
            return _configuration_error("OPENAI_API_KEY")
        with urllib.request.urlopen(self._request(messages, model, options, False), timeout=120) as response:
            data = json.loads(response.read())
        content = data["choices"][0]["message"]["content"]
        return {"model": model or self.config.model, "message": {"role": "assistant", "content": content}, "done": True}

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
                    yield {"done": True}
                    return
                try:
                    token = json.loads(payload).get("choices", [{}])[0].get("delta", {}).get("content", "")
                except json.JSONDecodeError:
                    continue
                if token:
                    yield {"message": {"role": "assistant", "content": token}, "done": False}
        yield {"done": True}


class GeminiProvider(Provider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.config = ProviderConfig("gemini", model, bool(self.api_key), True)

    def chat_once(self, messages, model, options):
        if not self.api_key:
            return _configuration_error("GEMINI_API_KEY")
        used_model = model or self.config.model
        contents = [
            {
                "role": "model" if item.get("role") == "assistant" else "user",
                "parts": [{"text": item.get("content", "")}],
            }
            for item in messages if item.get("role") != "system"
        ]
        system = "\n\n".join(item.get("content", "") for item in messages if item.get("role") == "system")
        body = {"contents": contents, "generationConfig": {"temperature": options.get("temperature", 0.7)}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{used_model}:generateContent?key={self.api_key}"
        request = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read())
        content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"model": used_model, "message": {"role": "assistant", "content": content}, "done": True}



class QwenMLXProvider(Provider):
    """Native local Qwen Coder provider powered by Apple MLX.

    The model loads lazily on the first generation request, so importing
    GPT-Doug does not allocate model weights or probe any network service.
    No Ollama daemon or localhost API is required.
    """

    def __init__(self):
        self.model_name = os.environ.get(
            "QWEN_MODEL",
            os.environ.get(
                "GPT_DOUG_MODEL",
                "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
            ),
        )

        self._model = None
        self._tokenizer = None

        mlx_ready = importlib.util.find_spec("mlx_lm") is not None

        self.config = ProviderConfig(
            "qwen",
            self.model_name,
            mlx_ready,
            True,
        )

    def health(self):
        result = super().health()

        result.update({
            "backend": "qwen",
            "provider": "qwen",
            "runtime": "mlx",
            "local": True,
            "ollama": False,
            "model_loaded": self._model is not None,
            "architecture": platform.machine(),
            "message": (
                "Qwen Coder / MLX ready"
                if self.config.configured
                else "mlx-lm is not installed"
            ),
        })

        return result

    def _ensure_loaded(self):
        if not self.config.configured:
            raise RuntimeError(
                "Qwen provider requires mlx-lm. "
                "Install it with: python -m pip install mlx-lm"
            )

        if self._model is not None:
            return

        from mlx_lm import load

        self._model, self._tokenizer = load(
            self.model_name
        )

    def _fit_messages(self, messages):
        """Keep system instructions plus recent conversation within a
        configurable lightweight local-context budget.
        """

        budget = int(
            os.environ.get(
                "QWEN_MAX_CONTEXT_CHARS",
                "36000",
            )
        )

        system_messages = [
            item
            for item in messages
            if item.get("role") == "system"
        ]

        conversation = [
            item
            for item in messages
            if item.get("role") != "system"
        ]

        used = sum(
            len(item.get("content", ""))
            for item in system_messages
        )

        selected = []

        for item in reversed(conversation):
            size = len(
                item.get("content", "")
            )

            if selected and used + size > budget:
                break

            selected.append(item)
            used += size

        selected.reverse()

        return system_messages + selected

    def chat_once(self, messages, model, options):
        self._ensure_loaded()

        from mlx_lm import generate

        used_model = model or self.model_name

        fitted = self._fit_messages(messages)

        prompt = self._tokenizer.apply_chat_template(
            fitted,
            tokenize=False,
            add_generation_prompt=True,
        )

        max_tokens = int(
            options.get(
                "max_tokens",
                options.get(
                    "num_predict",
                    os.environ.get(
                        "QWEN_MAX_TOKENS",
                        "1200",
                    ),
                ),
            )
        )

        content = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False,
        )

        return {
            "model": used_model,
            "backend": "qwen",
            "provider": "qwen",
            "runtime": "mlx",
            "message": {
                "role": "assistant",
                "content": content,
            },
            "done": True,
            "local": True,
        }

class OllamaProvider(Provider):
    """Legacy local provider. Constructed only after explicit opt-in."""

    def __init__(self):
        model = os.environ.get("OLLAMA_MODEL", os.environ.get("GPT_DOUG_MODEL", "gpt-doug"))
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.config = ProviderConfig("ollama", model, True, True)

    def chat_once(self, messages, model, options):
        body = json.dumps({"model": model or self.config.model, "messages": messages, "stream": False, "options": options}).encode()
        request = urllib.request.Request(f"{self.base_url}/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read())

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
                yield event
                if event.get("done"):
                    return


def _configuration_error(variable: str) -> Event:
    return {
        "message": {"role": "assistant", "content": f"The selected provider is not configured. Set {variable} or choose GPT_DOUG_PROVIDER=none."},
        "done": True,
        "error": "provider_not_configured",
    }


PROVIDER_FACTORIES = {
    "none": NoProvider,
    "qwen": QwenMLXProvider,
    "mlx": QwenMLXProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def _load_provider() -> Provider:
    name = os.environ.get("GPT_DOUG_PROVIDER", "none").strip().lower() or "none"
    factory = PROVIDER_FACTORIES.get(name)
    if factory is None:
        return NoProvider()
    return factory()


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
        {
            "id": "qwen",
            "label": "GPT-Doug × Qwen Coder (Local MLX)",
            "configured": importlib.util.find_spec("mlx_lm") is not None,
        },
        {"id": "openai", "label": "OpenAI", "configured": bool(os.environ.get("OPENAI_API_KEY"))},
        {"id": "gemini", "label": "Google Gemini", "configured": bool(os.environ.get("GEMINI_API_KEY"))},
        {"id": "ollama", "label": "Ollama (optional)", "configured": False},
    ]
