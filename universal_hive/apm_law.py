from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent / "apm_law.json"


class APMLaw:
    """Canonical project-level Adaptive Procedural Memory law."""

    def __init__(self) -> None:
        self.document = json.loads(_PATH.read_text(encoding="utf-8"))
        self.by_id = {
            item["id"]: item
            for item in self.document.get("laws", [])
        }

    @property
    def law_id(self) -> str:
        return str(self.document["law_id"])

    @property
    def axiom(self) -> str:
        return str(self.document["axiom"])

    def status(self) -> dict[str, Any]:
        return {
            "law_id": self.law_id,
            "name": self.document["name"],
            "short_name": self.document["short_name"],
            "status": self.document["status"],
            "scope": self.document["scope"],
            "application_rule": self.document["application_rule"],
            "external_legal_status": self.document["external_legal_status"],
            "rules": list(self.by_id),
        }

    def validate_procedure(
        self,
        procedure: Mapping[str, Any],
        *,
        requires_mutation: bool,
    ) -> dict[str, Any]:
        provenance = procedure.get("provenance")
        verified = bool(procedure.get("procedure_verified") or procedure.get("verified"))
        authorization_boundary = procedure.get("authorization_boundary")
        context_validation = procedure.get("context_validation")
        rollback = procedure.get("rollback") or procedure.get("recovery")

        checks = {
            "APM-PROVENANCE": bool(provenance),
            "APM-VERIFICATION": verified,
            "APM-REVALIDATE": bool(context_validation),
            "APM-AUTHORITY": bool(authorization_boundary),
            "APM-REVERSIBILITY": (not requires_mutation) or bool(rollback),
        }
        failed = [law_id for law_id, passed in checks.items() if not passed]
        return {
            "law_id": self.law_id,
            "valid": not failed,
            "checks": checks,
            "failed": failed,
        }
