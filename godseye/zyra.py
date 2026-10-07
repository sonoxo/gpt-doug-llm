from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _default_path() -> Path:
    return Path(__file__).resolve().parents[1] / "safety-shield" / "ontology" / "zyra-mss-v1.json"


def zyra_status(*, path: Optional[Path] = None) -> Dict[str, Any]:
    source = Path(path) if path is not None else _default_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("ZYRA MSS ontology must be a JSON object")
        fleet = payload.get("logical_agent_fleet") if isinstance(payload.get("logical_agent_fleet"), dict) else {}
        governed = payload.get("governed_actions") if isinstance(payload.get("governed_actions"), dict) else {}
        blocked = governed.get("BLOCK") if isinstance(governed.get("BLOCK"), list) else []
        return {
            "schema": "gpt-doug.zyra-status.v1",
            "status": "ONLINE",
            "partial": False,
            "errors": [],
            "ontology": payload.get("ontology"),
            "mode": payload.get("mode"),
            "logicalAgentCount": fleet.get("count"),
            "agentAuthority": fleet.get("agent_authority"),
            "automaticExternalAction": bool(fleet.get("automatic_external_action", False)),
            "blockedActionCount": len(blocked),
            "sourceCount": 1,
            "provenance": [str(source)],
            "payload": payload,
        }
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": "gpt-doug.zyra-status.v1",
            "status": "DEGRADED",
            "partial": True,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "ontology": None,
            "mode": None,
            "logicalAgentCount": None,
            "agentAuthority": None,
            "automaticExternalAction": False,
            "blockedActionCount": 0,
            "sourceCount": 0,
            "provenance": [str(source)],
            "payload": {},
        }
