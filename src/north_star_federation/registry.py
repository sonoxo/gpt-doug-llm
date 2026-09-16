"""Registry and validation helpers for THE NORTH STAR FEDERATION.

The registry is intentionally dependency-free and read-only. It describes
federation membership and governance metadata; it does not grant external
permissions or execute member actions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "federation" / "registry.json"

REQUIRED_MEMBER_FIELDS = {
    "id",
    "name",
    "role",
    "status",
    "canonical_source",
    "capabilities",
    "authority_boundary",
}

ALLOWED_STATUS = {"implemented", "source-linked", "integration-ready", "planned"}


class RegistryError(ValueError):
    """Raised when the federation registry violates its schema contract."""


def load_registry(path: Path | str = DEFAULT_REGISTRY) -> dict[str, Any]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("registry root must be an object")
    return data


def validate_registry(data: dict[str, Any]) -> list[str]:
    """Return a list of validation errors. An empty list means valid."""

    errors: list[str] = []
    for key in ("schema_version", "federation_id", "display_name", "north_star", "members"):
        if key not in data:
            errors.append(f"missing top-level field: {key}")

    members = data.get("members", [])
    if not isinstance(members, list) or not members:
        errors.append("members must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, member in enumerate(members):
        if not isinstance(member, dict):
            errors.append(f"member[{index}] must be an object")
            continue
        missing = REQUIRED_MEMBER_FIELDS - set(member)
        if missing:
            errors.append(f"member[{index}] missing fields: {', '.join(sorted(missing))}")
            continue

        member_id = member["id"]
        if not isinstance(member_id, str) or not member_id.strip():
            errors.append(f"member[{index}].id must be a non-empty string")
        elif member_id in seen:
            errors.append(f"duplicate member id: {member_id}")
        else:
            seen.add(member_id)

        if member.get("status") not in ALLOWED_STATUS:
            errors.append(f"member[{index}] has unsupported status: {member.get('status')}")

        capabilities = member.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append(f"member[{index}].capabilities must be a non-empty list")

        source = member.get("canonical_source")
        if not isinstance(source, str) or not source.startswith("https://github.com/"):
            errors.append(f"member[{index}].canonical_source must be a GitHub HTTPS URL")

    contract = data.get("decision_contract")
    if not isinstance(contract, dict):
        errors.append("decision_contract must be an object")
    else:
        for key, value in contract.items():
            if not isinstance(value, bool):
                errors.append(f"decision_contract.{key} must be boolean")

    return errors


def get_member(data: dict[str, Any], member_id: str) -> dict[str, Any] | None:
    for member in data.get("members", []):
        if member.get("id") == member_id:
            return member
    return None


def summary(data: dict[str, Any]) -> dict[str, Any]:
    members = data.get("members", [])
    return {
        "federation_id": data.get("federation_id"),
        "display_name": data.get("display_name"),
        "member_count": len(members),
        "implemented_count": sum(1 for member in members if member.get("status") == "implemented"),
        "integration_count": len(data.get("integrations", [])),
        "north_star": data.get("north_star"),
    }
