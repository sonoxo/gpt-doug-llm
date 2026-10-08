from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .capabilities import CAPABILITIES_BY_NAME
from .policy import CapabilityPolicy


CapabilityHandler = Callable[..., Any]


@dataclass(slots=True)
class RegisteredCapability:
    name: str
    handler: CapabilityHandler


class CapabilityBroker:
    """Dispatches capability calls through policy and optional resource scopes."""

    def __init__(self, policy: CapabilityPolicy) -> None:
        self.policy = policy
        self._handlers: dict[str, RegisteredCapability] = {}

    def register(self, name: str, handler: CapabilityHandler) -> None:
        if name not in CAPABILITIES_BY_NAME:
            raise ValueError(f"unknown capability: {name}")
        self._handlers[name] = RegisteredCapability(name=name, handler=handler)

    def registered(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def invoke(self, name: str, *args: Any, scope: str | None = None, **kwargs: Any) -> Any:
        if name not in CAPABILITIES_BY_NAME:
            raise ValueError(f"unknown capability: {name}")
        spec = CAPABILITIES_BY_NAME[name]
        self.policy.require(frozenset({name}))
        if spec.requires_scope:
            if not scope:
                raise PermissionError(f"scope required for capability: {name}")
            self.policy.require_scope(name, scope)
        registered = self._handlers.get(name)
        if registered is None:
            raise LookupError(f"no handler registered for capability: {name}")
        return registered.handler(*args, **kwargs)
