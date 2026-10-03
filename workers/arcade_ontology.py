"""Ontology-backed XUNIA Arcade bounty bridge.

Arcade completions become auditable ontology objects. Browser receipts are
client-attested, so XBC has no cash/crypto value and is not redeemable unless a
separate governed program explicitly approves redemption.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ARCADE_DIR = ROOT / "arcade"
RUNS_DIR = ARCADE_DIR / "runs"
CLAIMS_DIR = ARCADE_DIR / "claims"

sys.path.insert(0, str(ROOT))
import ontology_workers  # noqa: E402

XBC_UNIT = "XBC"

BOUNTIES = {
    "pulse-flight": {
        "milestone_id": "pulse-knowledge-lock-v1",
        "reward_xbc": 25,
        "ontology_function": "task_knowledge",
        "description": "Demonstrate stable signal matching, then query Task --referenced--> KnowledgeEntry links.",
    },
    "grid-drop": {
        "milestone_id": "grid-snapshot-v1",
        "reward_xbc": 50,
        "ontology_function": "snapshot",
        "description": "Charge the full node grid, then persist an ontology snapshot.",
    },
    "nova-tycoon": {
        "milestone_id": "nova-status-v1",
        "reward_xbc": 50,
        "ontology_function": "status",
        "description": "Reach reactor level 3, then inspect live ontology object/link counts.",
    },
    "orbit-runner": {
        "milestone_id": "orbit-link-traverse-v1",
        "reward_xbc": 50,
        "ontology_function": "task_result",
        "description": "Collect three graph stars, then traverse Task --produced--> Result links.",
    },
    "signal-match": {
        "milestone_id": "signal-knowledge-audit-v1",
        "reward_xbc": 50,
        "ontology_function": "knowledge",
        "description": "Score 50 with at most three misses, then audit KnowledgeEntry objects.",
    },
}


class ArcadeValidationError(ValueError):
    pass


def bounty_catalog() -> dict[str, dict[str, Any]]:
    return {game_id: dict(spec) for game_id, spec in BOUNTIES.items()}


def _safe_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise ArcadeValidationError(f"{field} must match [A-Za-z0-9_.:-] and be <=160 chars")
    return value


def _metrics(receipt: dict[str, Any]) -> dict[str, Any]:
    metrics = receipt.get("metrics")
    if not isinstance(metrics, dict):
        raise ArcadeValidationError("metrics must be an object")
    return metrics


def _eligible(game_id: str, metrics: dict[str, Any]) -> bool:
    if game_id == "pulse-flight":
        return int(metrics.get("score", 0)) >= 50 and int(metrics.get("streak_peak", 0)) >= 3
    if game_id == "grid-drop":
        return int(metrics.get("charged", 0)) >= 25
    if game_id == "nova-tycoon":
        return int(metrics.get("level", 0)) >= 3
    if game_id == "orbit-runner":
        return int(metrics.get("stars", 0)) >= 3
    if game_id == "signal-match":
        return int(metrics.get("score", 0)) >= 50 and int(metrics.get("misses", 999)) <= 3
    return False


def _execute_ecosystem_function(game_id: str, receipt_id: str) -> dict[str, Any]:
    """Execute only bounded ontology read/audit actions; never auto-submit tasks."""
    if game_id == "pulse-flight":
        links = ontology_workers.link_task_to_knowledge(
            receipt_id,
            "ontology task result knowledge zyra",
            top_n=3,
        )
        return {"function": "task_knowledge", "links": links}

    if game_id == "grid-drop":
        return {"function": "snapshot", "snapshot": ontology_workers.write_snapshot()}

    if game_id == "nova-tycoon":
        return {"function": "status", "status": ontology_workers.summary()}

    if game_id == "orbit-runner":
        tasks = ontology_workers.list_tasks()
        links = [ontology_workers.link_task_to_result(t["id"]) for t in tasks[:25]]
        return {"function": "task_result", "links": links, "tasks_examined": len(tasks[:25])}

    knowledge = ontology_workers.list_knowledge()
    return {
        "function": "knowledge",
        "knowledge_count": len(knowledge),
        "sample_ids": [str(k.get("id")) for k in knowledge[:10]],
    }


def record_arcade_run_action(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate an arcade milestone, execute its bounded ontology function, and award XBC."""
    if not isinstance(receipt, dict):
        raise ArcadeValidationError("receipt must be an object")

    receipt_id = _safe_id(receipt.get("receipt_id"), "receipt_id")
    game_id = _safe_id(receipt.get("game_id"), "game_id")
    if game_id not in BOUNTIES:
        raise ArcadeValidationError(f"unsupported game_id: {game_id}")

    milestone_id = _safe_id(receipt.get("milestone_id"), "milestone_id")
    spec = BOUNTIES[game_id]
    if milestone_id != spec["milestone_id"]:
        raise ArcadeValidationError("milestone_id does not match bounty catalog")

    metrics = _metrics(receipt)
    if not _eligible(game_id, metrics):
        raise ArcadeValidationError("milestone metrics do not qualify for bounty")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = RUNS_DIR / f"{receipt_id}.json"
    claim_path = CLAIMS_DIR / f"{receipt_id}.json"

    if claim_path.exists():
        return json.loads(claim_path.read_text())

    execution = _execute_ecosystem_function(game_id, receipt_id)
    run = {
        "object_type": "ArcadeRun",
        "receipt_id": receipt_id,
        "game_id": game_id,
        "milestone_id": milestone_id,
        "metrics": metrics,
        "created_at": receipt.get("created_at"),
        "source": receipt.get("source", "xunia.org/arcade"),
        "trust_level": "client-attested",
        "ontology_execution": execution,
    }
    run_path.write_text(json.dumps(run, indent=2))

    claim = {
        "object_type": "BountyClaim",
        "claim_id": f"bounty:{receipt_id}",
        "receipt_id": receipt_id,
        "game_id": game_id,
        "milestone_id": milestone_id,
        "reward": {"unit": XBC_UNIT, "amount": spec["reward_xbc"]},
        "status": "awarded",
        "redeemable": False,
        "cash_value": None,
        "trust_level": "client-attested",
        "link": {
            "link_type": "awarded_for",
            "from": ["BountyClaim", f"bounty:{receipt_id}"],
            "to": ["ArcadeRun", receipt_id],
        },
        "ontology_execution": execution,
    }
    claim_path.write_text(json.dumps(claim, indent=2))
    return claim


def list_arcade_runs() -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    return [data for p in sorted(RUNS_DIR.glob("*.json")) if (data := ontology_workers._read_json_safe(p))]


def list_bounty_claims() -> list[dict[str, Any]]:
    if not CLAIMS_DIR.exists():
        return []
    return [data for p in sorted(CLAIMS_DIR.glob("*.json")) if (data := ontology_workers._read_json_safe(p))]


def bounty_balance() -> dict[str, Any]:
    claims = list_bounty_claims()
    return {
        "unit": XBC_UNIT,
        "awarded": sum(int(c.get("reward", {}).get("amount", 0)) for c in claims if c.get("status") == "awarded"),
        "claim_count": len(claims),
        "redeemable": False,
    }
