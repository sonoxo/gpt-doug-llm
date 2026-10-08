from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .atomic import AtomicEnvelope, AtomicLayer
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

    def invoke_atomic(
        self,
        envelope: AtomicEnvelope,
        name: str,
        *args: Any,
        scope: str | None = None,
        **kwargs: Any,
    ) -> tuple[AtomicEnvelope, Any]:
        """Invoke one capability as an atom and return a molecule result envelope.

        Arguments and return values are intentionally not copied into the envelope.
        The envelope records only execution metadata, preserving traceability without
        turning the audit path into a secret/data exfiltration channel.
        """

        if envelope.layer is AtomicLayer.PARTICLE:
            atom = envelope.promote(
                AtomicLayer.ATOM,
                kind="capability-call",
                payload={
                    "capability": name,
                    "scope_present": scope is not None,
                },
            )
        elif envelope.layer is AtomicLayer.ATOM:
            atom = envelope
        else:
            raise ValueError(
                "atomic capability invocation requires a particle or atom envelope"
            )

        result = self.invoke(name, *args, scope=scope, **kwargs)
        molecule = atom.promote(
            AtomicLayer.MOLECULE,
            kind="capability-result",
            payload={
                "capability": name,
                "status": "succeeded",
                "scope_present": scope is not None,
            },
        )
        return molecule, result
