from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class ModelProvider(Protocol):
    name: str

    def propose(self, prompt: str) -> str: ...

    def review(self, prompt: str) -> str: ...


@dataclass
class CallableProvider:
    name: str
    propose_fn: Callable[[str], str]
    review_fn: Callable[[str], str]

    def propose(self, prompt: str) -> str:
        return self.propose_fn(prompt)

    def review(self, prompt: str) -> str:
        return self.review_fn(prompt)


class ProviderRegistry:
    """Opt-in registry for authorized model adapters.

    No external provider is contacted unless an adapter is explicitly registered
    by the operator. API keys and credentials never belong in this package.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        if not provider.name.strip():
            raise ValueError("provider name cannot be empty")
        self._providers[provider.name] = provider

    def names(self) -> list[str]:
        return sorted(self._providers)

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"provider not registered: {name}") from exc

    def ensemble_review(self, prompt: str) -> dict[str, str]:
        return {name: provider.review(prompt) for name, provider in sorted(self._providers.items())}
