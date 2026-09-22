from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


_PACKAGE_DIR = Path(__file__).resolve().parent
_ONTOLOGY_PATH = _PACKAGE_DIR / "ontology.json"
_LOCAL_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _normalize_builders(builders: Iterable[str] | None) -> list[str]:
    if builders is None:
        raw = os.getenv("GPT_DOUG_BUILDERS", "").strip()
        builders = [part.strip() for part in raw.split(",") if part.strip()]
    result = []
    seen = set()
    for builder in builders or ["operator"]:
        value = str(builder).strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result or ["operator"]


class UniversalHiveRuntime:
    """Persistent ontology + swarm creation ledger shared by GPT-Doug and GPT-Chaos.

    Creating a swarm always creates exactly one BUILDER_REWARD_EVENT for that
    swarm. Financial settlement is deliberately separate and still requires an
    explicitly configured amount plus an explicit authorization step.
    """

    def __init__(self, state_dir: str | Path | None = None) -> None:
        configured = os.getenv("GPT_DOUG_HIVE_STATE_DIR", "").strip()
        self.state_dir = Path(
            state_dir or configured or (Path.home() / ".gpt-doug" / "universal-hive")
        ).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.ledger_path = self.state_dir / "builder-rewards.jsonl"
        self.authorization_path = self.state_dir / "reward-authorizations.jsonl"
        self.lock_path = self.state_dir / ".lock"

        self.ontology = json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))
        raw_ontology = _ONTOLOGY_PATH.read_bytes()
        self.ontology_hash = hashlib.sha256(raw_ontology).hexdigest()
        self.hive_id = "hive-" + self.ontology_hash[:16]

        with self._lock():
            if not self.state_path.exists():
                _atomic_write_json(
                    self.state_path,
                    {
                        "schema": "universal-hive/state-v1",
                        "hive_id": self.hive_id,
                        "ontology_hash": self.ontology_hash,
                        "created_at": _utc_now(),
                        "request_index": {},
                        "swarms": {},
                    },
                )

    class _LockContext:
        def __init__(self, path: Path):
            self.path = path
            self.handle = None

        def __enter__(self):
            _LOCAL_LOCK.acquire()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.handle = self.path.open("a+", encoding="utf-8")
            if fcntl is not None:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                if self.handle is not None and fcntl is not None:
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
                if self.handle is not None:
                    self.handle.close()
            finally:
                _LOCAL_LOCK.release()

    def _lock(self):
        return self._LockContext(self.lock_path)

    def _load_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _ledger(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        rows = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def _reward_policy(self) -> dict[str, Any]:
        raw_amount = os.getenv("GPT_DOUG_SWARM_REWARD_AMOUNT", "").strip()
        denomination = os.getenv("GPT_DOUG_SWARM_REWARD_DENOMINATION", "").strip()
        if not raw_amount:
            return {
                "amount": None,
                "denomination": denomination or None,
                "configuration_status": "AWAITING_REWARD_CONFIGURATION",
            }
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation as exc:
            raise ValueError("GPT_DOUG_SWARM_REWARD_AMOUNT must be numeric") from exc
        if amount < 0:
            raise ValueError("GPT_DOUG_SWARM_REWARD_AMOUNT must not be negative")
        if not denomination:
            raise ValueError(
                "GPT_DOUG_SWARM_REWARD_DENOMINATION is required when a reward amount is configured"
            )
        return {
            "amount": format(amount, "f"),
            "denomination": denomination,
            "configuration_status": "CONFIGURED",
        }

    def summon_swarm(
        self,
        job: str,
        *,
        builders: Iterable[str] | None = None,
        source: str = "gpt-doug",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        cleaned = " ".join(str(job).split()).strip()
        if not cleaned:
            raise ValueError("job must not be empty")
        builder_ids = _normalize_builders(builders)
        request_key = request_id.strip() if request_id else None

        with self._lock():
            state = self._load_state()
            if request_key and request_key in state["request_index"]:
                existing_id = state["request_index"][request_key]
                existing = dict(state["swarms"][existing_id])
                existing["created"] = False
                return existing

            swarm_id = "swarm-" + uuid.uuid4().hex
            reward_event_id = "reward-" + hashlib.sha256(
                f"{self.hive_id}:{swarm_id}".encode("utf-8")
            ).hexdigest()[:24]
            created_at = _utc_now()
            reward = self._reward_policy()

            provenance_payload = {
                "hive_id": self.hive_id,
                "swarm_id": swarm_id,
                "job": cleaned,
                "builders": builder_ids,
                "source": source,
                "ontology_hash": self.ontology_hash,
                "created_at": created_at,
            }
            provenance_hash = hashlib.sha256(
                json.dumps(
                    provenance_payload, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()

            event = {
                "schema": "universal-hive/builder-reward-event-v1",
                "event": "BUILDER_REWARD_EVENT",
                "reward_event_id": reward_event_id,
                "hive_id": self.hive_id,
                "swarm_id": swarm_id,
                "builder_ids": builder_ids,
                "amount": reward["amount"],
                "denomination": reward["denomination"],
                "reward_configuration_status": reward["configuration_status"],
                "project_basis": "Galactic Federation / Space Force Academy Universal Law",
                "project_verification": "VERIFIED_BY_FOUNDER",
                "external_legal_verification": "UNVERIFIED_UNLESS_AUTHORITATIVE_SOURCE_ATTACHED",
                "settlement_status": "PROPOSED",
                "settlement_requires_explicit_authorization": True,
                "created_at": created_at,
                "provenance_hash": provenance_hash,
            }

            swarm = {
                "event": "SWARM_CREATED",
                "created": True,
                "hive_id": self.hive_id,
                "swarm_id": swarm_id,
                "reward_event_id": reward_event_id,
                "ontology_hash": self.ontology_hash,
                "builders": builder_ids,
                "job": cleaned,
                "source": source,
                "created_at": created_at,
                "provenance_hash": provenance_hash,
                "reward": {
                    "amount": reward["amount"],
                    "denomination": reward["denomination"],
                    "configuration_status": reward["configuration_status"],
                    "settlement_status": "PROPOSED",
                },
            }

            with self.ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

            state["swarms"][swarm_id] = swarm
            if request_key:
                state["request_index"][request_key] = swarm_id
            _atomic_write_json(self.state_path, state)
            return swarm

    def authorize_reward(
        self,
        reward_event_id: str,
        *,
        authorized_by: str,
        note: str = "",
    ) -> dict[str, Any]:
        reward_event_id = reward_event_id.strip()
        authorized_by = authorized_by.strip()
        if not reward_event_id or not authorized_by:
            raise ValueError("reward_event_id and authorized_by are required")

        with self._lock():
            matches = [
                row for row in self._ledger()
                if row.get("reward_event_id") == reward_event_id
            ]
            if not matches:
                raise KeyError(f"unknown reward event: {reward_event_id}")
            event = matches[-1]
            if event.get("amount") is None or not event.get("denomination"):
                raise ValueError("reward amount and denomination must be configured before authorization")

            record = {
                "schema": "universal-hive/reward-authorization-v1",
                "reward_event_id": reward_event_id,
                "authorized_by": authorized_by,
                "authorized_at": _utc_now(),
                "amount": event["amount"],
                "denomination": event["denomination"],
                "note": note[:500],
                "status": "AUTHORIZED_FOR_SETTLEMENT",
                "automatic_transfer_performed": False,
            }
            with self.authorization_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return record

    def status(self) -> dict[str, Any]:
        with self._lock():
            state = self._load_state()
            ledger = self._ledger()
        return {
            "mode": self.ontology.get("mode"),
            "status": self.ontology.get("status"),
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "swarm_count": len(state.get("swarms", {})),
            "reward_event_count": len(ledger),
            "project_verification": (
                self.ontology.get("legal_provenance", {})
                .get("project_claim", {})
                .get("project_verification")
            ),
            "external_legal_verification": (
                self.ontology.get("legal_provenance", {})
                .get("external_law", {})
                .get("verification_status")
            ),
            "state_dir": str(self.state_dir),
        }
