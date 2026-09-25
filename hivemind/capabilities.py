from __future__ import annotations

import importlib.util
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from .registry import INTEGRATIONS
from .types import Capability, Integration


def probe_integration(integration: Integration) -> Capability:
    kind = integration.probe_kind
    value = integration.probe_value

    if kind == "command":
        found = shutil.which(value)
        return Capability(integration, bool(found), found or f"command not found: {value}")

    if kind == "python_module":
        found = importlib.util.find_spec(value)
        return Capability(
            integration,
            found is not None,
            f"python module available: {value}" if found else f"python module not found: {value}",
        )

    if kind == "env":
        configured = os.getenv(value, "").strip()
        return Capability(
            integration,
            bool(configured),
            f"configured via {value}" if configured else f"environment variable not set: {value}",
        )

    if kind == "reference":
        return Capability(integration, True, "reference integration; no runtime probe required")

    return Capability(integration, False, f"unknown probe kind: {kind}")


def doctor(max_workers: int = 8) -> list[Capability]:
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(probe_integration, INTEGRATIONS))
