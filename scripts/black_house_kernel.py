#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "the-black-house" / "kernel" / "kernel.manifest.json"


class KernelContractError(ValueError):
    pass


def load_kernel() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def validate_kernel(kernel: dict[str, Any] | None = None) -> dict[str, Any]:
    kernel = kernel or load_kernel()
    required = {
        "schemaVersion",
        "kernelVersion",
        "controlPlane",
        "missionProtocol",
        "authority",
        "objectTypes",
        "relationshipTypes",
        "invariants",
        "bindings",
    }
    missing = sorted(required.difference(kernel))
    if missing:
        raise KernelContractError(f"missing kernel fields: {', '.join(missing)}")
    if kernel["kernelVersion"] != "3.0.0":
        raise KernelContractError("kernelVersion must be 3.0.0")
    if kernel["controlPlane"] != "THE_BLACK_HOUSE_V1":
        raise KernelContractError("controlPlane mismatch")
    if len(kernel["objectTypes"]) != len(set(kernel["objectTypes"])):
        raise KernelContractError("duplicate object types")
    if len(kernel["relationshipTypes"]) != len(set(kernel["relationshipTypes"])):
        raise KernelContractError("duplicate relationship types")
    if not all(kernel["invariants"].values()):
        raise KernelContractError("all kernel invariants must fail closed")
    return kernel


def require_object_type(object_type: str) -> str:
    kernel = validate_kernel()
    if object_type not in kernel["objectTypes"]:
        raise KernelContractError(f"unregistered object type: {object_type}")
    return object_type


def require_relationship(relation: str) -> str:
    kernel = validate_kernel()
    if relation not in kernel["relationshipTypes"]:
        raise KernelContractError(f"unregistered relationship: {relation}")
    return relation


def kernel_status() -> dict[str, Any]:
    kernel = validate_kernel()
    return {
        "status": "GREEN",
        "kernelVersion": kernel["kernelVersion"],
        "controlPlane": kernel["controlPlane"],
        "missionProtocol": kernel["missionProtocol"],
        "objectTypes": len(kernel["objectTypes"]),
        "relationshipTypes": len(kernel["relationshipTypes"]),
        "bindings": [item["component"] for item in kernel["bindings"]],
    }


if __name__ == "__main__":
    print(json.dumps(kernel_status(), indent=2, sort_keys=True))
