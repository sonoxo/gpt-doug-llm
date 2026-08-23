"""Anthropic Mythos bridge for GPT-Doug.

This module does not copy, redistribute, or modify Anthropic model weights.
It routes GPT-Doug requests through Anthropic's Messages API using the existing
:class:`agents.llm_backend.AnthropicProvider` implementation.

Claude Mythos 5 requires Anthropic authorization. The bridge never attempts to
bypass provider access controls. When enabled, an unavailable Mythos request may
fall back to Claude Fable 5, which Anthropic documents as the broadly available
safeguarded counterpart.
"""

from __future__ import annotations

import os
import urllib.error

from agents.llm_backend import AnthropicProvider, ProviderConfig

MYTHOS_MODEL = "claude-mythos-5"
FABLE_MODEL = "claude-fable-5"
_FALLBACK_HTTP_CODES = {400, 403, 404}


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class MythosProvider(AnthropicProvider):
    """GPT-Doug provider profile targeting Claude Mythos 5.

    The existing Anthropic API credential is reused. Mythos authorization is
    determined exclusively by Anthropic; this class cannot grant or bypass it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.mythos_model = os.environ.get("ANTHROPIC_MYTHOS_MODEL", MYTHOS_MODEL).strip() or MYTHOS_MODEL
        self.fallback_model = (
            os.environ.get("ANTHROPIC_MYTHOS_FALLBACK_MODEL", FABLE_MODEL).strip()
            or FABLE_MODEL
        )
        self.fallback_enabled = _env_flag("ANTHROPIC_MYTHOS_FALLBACK", True)
        self.config = ProviderConfig(
            "mythos",
            self.mythos_model,
            self.config.configured,
            False,
        )

    def health(self) -> dict:
        state = super().health()
        return {
            **state,
            "backend": "mythos",
            "provider": "mythos",
            "model": self.mythos_model,
            "models": [self.mythos_model, self.fallback_model],
            "mythos_access": "anthropic_authorization_required",
            "fallback_enabled": self.fallback_enabled,
            "fallback_model": self.fallback_model,
            "message": (
                "Anthropic credential configured; Mythos access is verified by Anthropic at request time"
                if self.config.configured
                else "Set ANTHROPIC_API_KEY to use the Mythos provider profile"
            ),
        }

    def chat_once(self, messages, model, options):
        requested_model = model or self.mythos_model
        try:
            result = super().chat_once(messages, requested_model, options)
            return {
                **result,
                "provider": "mythos",
                "requested_model": requested_model,
                "fallback_used": False,
            }
        except urllib.error.HTTPError as exc:
            if (
                not self.fallback_enabled
                or requested_model == self.fallback_model
                or exc.code not in _FALLBACK_HTTP_CODES
            ):
                raise
            result = super().chat_once(messages, self.fallback_model, options)
            return {
                **result,
                "provider": "mythos",
                "requested_model": requested_model,
                "model": self.fallback_model,
                "fallback_used": True,
                "fallback_reason": f"mythos_http_{exc.code}",
            }
