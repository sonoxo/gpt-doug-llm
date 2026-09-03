#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"
CORE_PATH = KNOWLEDGE_DIR / "rvia-agentic-core.json"
MODULE_PATHS = (
    KNOWLEDGE_DIR / "palantir-stack-v1.json",
    KNOWLEDGE_DIR / "replit-stripe-payments-v1.json",
)
EXPECTED_CORE_PROFILE = "rvia-agentic-core-v1"


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"Knowledge artifact must be a JSON object: {path.name}")
    return data


def _module_id(data: dict, path: Path) -> str:
    module_id = data.get("knowledge_id") or data.get("profile")
    if not isinstance(module_id, str) or not module_id.strip():
        raise RuntimeError(f"Knowledge module missing knowledge_id/profile: {path.name}")
    return module_id


def load_knowledge_bundle() -> dict:
    core = _load_json(CORE_PATH)
    if core.get("profile") != EXPECTED_CORE_PROFILE:
        raise RuntimeError(
            f"Unexpected knowledge profile: {core.get('profile')!r}; expected {EXPECTED_CORE_PROFILE!r}"
        )

    modules: list[dict] = []
    seen: set[str] = set()
    for path in MODULE_PATHS:
        data = _load_json(path)
        module_id = _module_id(data, path)
        if module_id in seen:
            raise RuntimeError(f"Duplicate knowledge module id: {module_id}")
        if not data.get("version"):
            raise RuntimeError(f"Knowledge module missing version: {path.name}")
        seen.add(module_id)
        modules.append(
            {
                "id": module_id,
                "version": str(data["version"]),
                "path": path.name,
                "data": data,
            }
        )

    return {
        "profile": core["profile"],
        "version": core["version"],
        "core": core,
        "modules": modules,
    }


def module_manifest() -> list[dict[str, str]]:
    bundle = load_knowledge_bundle()
    return [
        {"id": item["id"], "version": item["version"], "path": item["path"]}
        for item in bundle["modules"]
    ]


if __name__ == "__main__":
    print(json.dumps(module_manifest(), indent=2))
