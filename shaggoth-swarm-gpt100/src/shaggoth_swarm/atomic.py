from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from enum import IntEnum
from hashlib import sha256
from typing import Any, Iterable
from uuid import uuid4

from .models import utc_now


class AtomicLayer(IntEnum):
    PARTICLE = 0
    ATOM = 1
    MOLECULE = 2
    CELL = 3
    SWARM = 4
    SERVICE = 5
    FABRIC = 6
    GOVERNANCE = 7


@dataclass(frozen=True, slots=True)
class LayerSpec:
    layer: AtomicLayer
    name: str
    purpose: str
    dependencies: tuple[AtomicLayer, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    invariants: tuple[str, ...]


ATOMIC_STACK: tuple[LayerSpec, ...] = (
    LayerSpec(
        AtomicLayer.PARTICLE,
        "particle",
        "Immutable execution primitives: IDs, timestamps, envelopes, hashes, and typed state.",
        (),
        ("raw-input",),
        ("atomic-envelope",),
        (
            "every envelope has a unique id",
            "payload digest is deterministic",
            "creation timestamp is recorded",
        ),
    ),
    LayerSpec(
        AtomicLayer.ATOM,
        "atom",
        "One explicitly named capability invocation with policy and resource scope.",
        (AtomicLayer.PARTICLE,),
        ("atomic-envelope", "capability-request"),
        ("scoped-operation",),
        (
            "one atom maps to one capability",
            "scoped capabilities require an explicit resource scope",
            "capability must exist in the catalog",
        ),
    ),
    LayerSpec(
        AtomicLayer.MOLECULE,
        "molecule",
        "A bounded composition of atoms representing a plan or reusable operation.",
        (AtomicLayer.ATOM,),
        ("scoped-operation",),
        ("bounded-plan",),
        (
            "composition is finite",
            "dependencies are explicit",
            "each member atom remains independently auditable",
        ),
    ),
    LayerSpec(
        AtomicLayer.CELL,
        "cell",
        "A single agent execution boundary with identity, specialty, budget, and lifecycle.",
        (AtomicLayer.MOLECULE,),
        ("bounded-plan", "agent-spec"),
        ("agent-result",),
        (
            "one cell has one agent identity",
            "fanout is not performed inside the cell",
            "execution respects configured depth and capability policy",
        ),
    ),
    LayerSpec(
        AtomicLayer.SWARM,
        "swarm",
        "Bounded multi-agent coordination, fanout, aggregation, and consensus.",
        (AtomicLayer.CELL,),
        ("agent-result", "swarm-goal"),
        ("swarm-report",),
        (
            "fanout is capped",
            "agent results retain provenance",
            "aggregation cannot widen authority",
        ),
    ),
    LayerSpec(
        AtomicLayer.SERVICE,
        "service",
        "Stable API, queue, storage, catalog, and connector surfaces around the swarm.",
        (AtomicLayer.SWARM,),
        ("swarm-report", "service-request"),
        ("service-response", "telemetry-event"),
        (
            "service identity is visible",
            "external resources are explicitly configured",
            "secrets are referenced, not emitted",
        ),
    ),
    LayerSpec(
        AtomicLayer.FABRIC,
        "fabric",
        "Container, Kubernetes, network-policy, scaling, health, and deployment fabric.",
        (AtomicLayer.SERVICE,),
        ("service-image", "deployment-config"),
        ("running-service",),
        (
            "non-root by default",
            "health/readiness checks are available",
            "network access is bounded by deployment policy",
        ),
    ),
    LayerSpec(
        AtomicLayer.GOVERNANCE,
        "governance",
        "Cross-cutting policy, audit, provenance, risk, and compliance assertions.",
        (
            AtomicLayer.PARTICLE,
            AtomicLayer.ATOM,
            AtomicLayer.MOLECULE,
            AtomicLayer.CELL,
            AtomicLayer.SWARM,
            AtomicLayer.SERVICE,
            AtomicLayer.FABRIC,
        ),
        ("all-layer-events",),
        ("audit-record", "policy-decision", "provenance-record"),
        (
            "governance may restrict but never silently widen authority",
            "high-impact operations are attributable",
            "source provenance survives composition",
        ),
    ),
)


SPECS_BY_LAYER = {spec.layer: spec for spec in ATOMIC_STACK}
SPECS_BY_NAME = {spec.name: spec for spec in ATOMIC_STACK}


def validate_stack(stack: Iterable[LayerSpec] = ATOMIC_STACK) -> tuple[bool, tuple[str, ...]]:
    specs = tuple(stack)
    errors: list[str] = []
    seen_layers: set[AtomicLayer] = set()
    seen_names: set[str] = set()

    for spec in specs:
        if spec.layer in seen_layers:
            errors.append(f"duplicate layer id: {spec.layer.name}")
        seen_layers.add(spec.layer)
        if spec.name in seen_names:
            errors.append(f"duplicate layer name: {spec.name}")
        seen_names.add(spec.name)

        if spec.layer is not AtomicLayer.GOVERNANCE:
            for dependency in spec.dependencies:
                if dependency >= spec.layer:
                    errors.append(
                        f"{spec.name} depends on non-lower layer {dependency.name.lower()}"
                    )

    expected = set(AtomicLayer)
    missing = expected - seen_layers
    if missing:
        errors.append(
            "missing layers: " + ", ".join(sorted(layer.name.lower() for layer in missing))
        )

    governance = next((spec for spec in specs if spec.layer is AtomicLayer.GOVERNANCE), None)
    if governance is not None:
        required = set(AtomicLayer) - {AtomicLayer.GOVERNANCE}
        if set(governance.dependencies) != required:
            errors.append("governance must depend on every lower layer")

    return not errors, tuple(errors)


@dataclass(frozen=True, slots=True)
class AtomicEnvelope:
    kind: str
    payload: dict[str, Any]
    layer: AtomicLayer = AtomicLayer.PARTICLE
    id: str = field(default_factory=lambda: uuid4().hex)
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now)
    parent_id: str | None = None

    @property
    def digest(self) -> str:
        canonical = json.dumps(\n            self.payload, sort_keys=True, separators=(",", ":"), default=repr\n        ).encode("utf-8")\n        return sha256(canonical).hexdigest()

    def promote(
        self,
        target: AtomicLayer,
        *,
        kind: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> "AtomicEnvelope":
        validate_transition(self.layer, target)
        return AtomicEnvelope(
            kind=kind or self.kind,
            payload=dict(self.payload if payload is None else payload),
            layer=target,
            trace_id=self.trace_id,
            parent_id=self.id,
        )

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["layer"] = self.layer.name.lower()
        data["digest"] = self.digest
        return data


def validate_transition(source: AtomicLayer, target: AtomicLayer) -> None:
    if source is target:
        return
    if target is AtomicLayer.GOVERNANCE:
        return
    if source is AtomicLayer.GOVERNANCE:
        raise ValueError("governance records do not promote into execution layers")
    if target != source + 1:
        raise ValueError(
            f"invalid atomic transition: {source.name.lower()} -> {target.name.lower()}"
        )


def stack_manifest() -> dict[str, Any]:
    valid, errors = validate_stack()
    return {
        "name": "shaggoth-atomic-stack",
        "version": 1,
        "valid": valid,
        "errors": list(errors),
        "layer_count": len(ATOMIC_STACK),
        "layers": [
            {
                "id": int(spec.layer),
                "name": spec.name,
                "purpose": spec.purpose,
                "dependencies": [dependency.name.lower() for dependency in spec.dependencies],
                "inputs": list(spec.inputs),
                "outputs": list(spec.outputs),
                "invariants": list(spec.invariants),
            }
            for spec in ATOMIC_STACK
        ],
    }
