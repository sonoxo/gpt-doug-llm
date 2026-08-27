from __future__ import annotations

import json
from pathlib import Path

from agency_cloud.config import Settings


class IntelligenceIntegrationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntelligenceIntegrationError(f"cannot read intelligence package {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IntelligenceIntegrationError(f"expected intelligence object at {path}")
    return value


def live_changes(settings: Settings) -> dict:
    path = settings.repo_root / "intel" / "live" / "live-changes.json"
    if not path.exists():
        return {"status": "NO_BASELINE", "message": "run ZYRA /live-sync to establish a live-intel baseline"}
    return _read_json(path)


def ontology_status(settings: Settings) -> str:
    try:
        from agents.ontology_query import run_query_command

        return run_query_command(settings.repo_root, "status", "")
    except Exception as exc:  # boundary adapter converts implementation errors to API-safe status
        raise IntelligenceIntegrationError(f"ontology status unavailable: {exc}") from exc


def ontology_query(settings: Settings, question: str) -> str:
    if not question.strip():
        raise IntelligenceIntegrationError("ontology question is required")
    try:
        from agents.ontology_query import run_query_command

        return run_query_command(settings.repo_root, "query", question.strip())
    except Exception as exc:
        raise IntelligenceIntegrationError(f"locked ontology query unavailable: {exc}") from exc


def glassonion_status(settings: Settings) -> str:
    try:
        from agents.glassonion_layer import run_command

        return run_command(settings.repo_root, "status", "")
    except Exception as exc:
        raise IntelligenceIntegrationError(f"Glass Onion status unavailable: {exc}") from exc


def glassonion_query(settings: Settings, question: str) -> str:
    if not question.strip():
        raise IntelligenceIntegrationError("Glass Onion question is required")
    try:
        from agents.glassonion_layer import run_command

        return run_command(settings.repo_root, "query", question.strip())
    except Exception as exc:
        raise IntelligenceIntegrationError(f"Glass Onion query unavailable: {exc}") from exc


def lock_summary(settings: Settings) -> dict:
    result: dict[str, object] = {}
    packages = {
        "ontology": settings.repo_root / "intel" / "qtfy" / "master-lock.json",
        "glassonion": settings.repo_root / "intel" / "glassonion" / "glassonion-lock.json",
    }
    for name, path in packages.items():
        if not path.exists():
            result[name] = {"present": False}
            continue
        payload = _read_json(path)
        result[name] = {
            "present": True,
            "lockId": payload.get("lockId"),
            "locked": payload.get("locked", True),
            "publicationState": payload.get("publicationState"),
        }
    return result
