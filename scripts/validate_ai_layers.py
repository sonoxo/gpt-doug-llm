#!/usr/bin/env python3
"""Validate the canonical six-layer AI architecture manifest.

This gate is intentionally structural: it guarantees that all required AI layers are
explicitly declared and that each layer points to repository evidence. It does not
claim that every algorithm associated with a layer is implemented from scratch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "ai-layer-manifest.json"
CANONICAL = {
    "classical_ai",
    "machine_learning",
    "neural_networks",
    "deep_learning",
    "generative_ai",
    "agentic_ai",
}


def fail(message: str) -> None:
    print(f"AI-LAYER-GATE: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not MANIFEST.is_file():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")

    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load manifest: {exc}")

    required = set(data.get("required_layer_ids", []))
    if required != CANONICAL:
        fail(
            "required_layer_ids must contain exactly: "
            + ", ".join(sorted(CANONICAL))
        )

    layers = data.get("layers")
    if not isinstance(layers, list):
        fail("layers must be a list")

    seen: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            fail("each layer must be an object")

        layer_id = layer.get("id")
        if layer_id not in CANONICAL:
            fail(f"unknown layer id: {layer_id!r}")
        if layer_id in seen:
            fail(f"duplicate layer id: {layer_id}")
        seen.add(layer_id)

        name = layer.get("name")
        coverage = layer.get("coverage")
        capabilities = layer.get("capabilities")
        evidence = layer.get("evidence")

        if not isinstance(name, str) or not name.strip():
            fail(f"{layer_id}: missing name")
        if not isinstance(coverage, str) or not coverage.strip():
            fail(f"{layer_id}: missing coverage mode")
        if not isinstance(capabilities, list) or not capabilities:
            fail(f"{layer_id}: capabilities must be a non-empty list")
        if not isinstance(evidence, list) or not evidence:
            fail(f"{layer_id}: evidence must be a non-empty list")

        for rel in evidence:
            if not isinstance(rel, str) or not rel.strip():
                fail(f"{layer_id}: invalid evidence path {rel!r}")
            target = ROOT / rel
            if not target.exists():
                fail(f"{layer_id}: missing evidence path: {rel}")

    if seen != CANONICAL:
        fail("manifest does not define all six canonical layers")

    print("AI-LAYER-GATE: PASS")
    for layer in layers:
        print(
            f"- {layer['name']}: {layer['coverage']} "
            f"({len(layer['evidence'])} evidence path(s))"
        )


if __name__ == "__main__":
    main()
