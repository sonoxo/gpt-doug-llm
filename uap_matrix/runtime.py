from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


_LOCAL_LOCK = threading.RLock()
_PEERS = ("GPT_DOUG", "GPT_CHAOS")
_CHANNELS = (
    "OBSERVATION",
    "HYPOTHESIS",
    "EVIDENCE",
    "DISSENT",
    "PLAN",
    "ACTION",
    "RESULT",
    "FAULT",
    "RECOVERY",
)
_VOTES = {"SUPPORT", "DISSENT", "ABSTAIN"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


class UAPMatrixSharedSpace:
    """Persistent peer-intelligence blackboard for GPT-Doug and GPT-Chaos.

    UAP is a project label for the Unified Agent Plane. The runtime only
    coordinates local project state. It does not grant external authority,
    physical autonomy, or permission to bypass existing policy gates.
    """

    def __init__(
        self,
        state_dir: str | Path | None = None,
        *,
        hive_id: str | None = None,
        ontology_hash: str | None = None,
    ) -> None:
        configured = os.getenv("GPT_DOUG_UAP_MATRIX_STATE_DIR", "").strip()
        fallback = Path.home() / ".gpt-doug" / "universal-hive" / "uap-matrix"
        self.state_dir = Path(state_dir or configured or fallback).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.events_path = self.state_dir / "events.jsonl"
        self.checkpoint_dir = self.state_dir / "checkpoints"
        self.lock_path = self.state_dir / ".lock"
        self.hive_id = hive_id or "UNBOUND_HIVE"
        self.ontology_hash = ontology_hash or "UNBOUND_ONTOLOGY"
        matrix_seed = f"{self.hive_id}:{self.ontology_hash}:UAP_MATRIX_V1"
        self.matrix_id = "uap-" + hashlib.sha256(matrix_seed.encode("utf-8")).hexdigest()[:16]

        with self._locked():
            if not self.state_path.exists():
                _atomic_write_json(self.state_path, self._initial_state())
            else:
                existing = self._load_state()
                self.matrix_id = existing.get("matrix_id", self.matrix_id)
                self.hive_id = existing.get("hive_id", self.hive_id)
                self.ontology_hash = existing.get(
                    "ontology_hash", self.ontology_hash
                )

    def _initial_state(self) -> dict[str, Any]:
        return {
            "schema": "uap-matrix/shared-space-v1",
            "matrix_id": self.matrix_id,
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "mode": "PEER_INTELLIGENCE",
            "uap_expansion": "UNIFIED_AGENT_PLANE",
            "created_at": _utc_now(),
            "revision": 0,
            "head_event_id": None,
            "execution_authority": "NO_EXTERNAL_AUTHORITY_GRANTED",
            "human_authority": True,
            "agents": {
                peer: {
                    "status": "PEER",
                    "rights": [
                        "OBSERVE",
                        "PROPOSE",
                        "DISSENT",
                        "VOTE",
                        "CHECKPOINT",
                    ],
                }
                for peer in _PEERS
            },
            "blackboard": {channel: [] for channel in _CHANNELS},
            "decisions": {},
        }

    @contextmanager
    def _locked(self):
        _LOCAL_LOCK.acquire()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
            _LOCAL_LOCK.release()

    def _load_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_event(self, event: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _require_peer(self, agent: str) -> str:
        normalized = str(agent).strip().upper().replace("-", "_")
        if normalized not in _PEERS:
            raise ValueError(f"agent must be one of: {', '.join(_PEERS)}")
        return normalized

    def _require_channel(self, channel: str) -> str:
        normalized = str(channel).strip().upper()
        if normalized not in _CHANNELS:
            raise ValueError(f"channel must be one of: {', '.join(_CHANNELS)}")
        return normalized

    def publish(
        self,
        agent: str,
        channel: str,
        content: Any,
        *,
        evidence: Any | None = None,
        policy_status: str = "ADVISORY_ONLY",
    ) -> dict[str, Any]:
        peer = self._require_peer(agent)
        lane = self._require_channel(channel)
        event = {
            "schema": "uap-matrix/event-v1",
            "event_id": "evt-" + uuid.uuid4().hex,
            "matrix_id": self.matrix_id,
            "agent": peer,
            "peer_status": "PEER",
            "channel": lane,
            "content": _json_copy(content),
            "evidence": _json_copy(evidence),
            "policy_status": str(policy_status),
            "created_at": _utc_now(),
        }

        with self._locked():
            state = self._load_state()
            state["blackboard"][lane].append(event)
            state["revision"] = int(state.get("revision", 0)) + 1
            state["head_event_id"] = event["event_id"]
            self._write_event(event)
            _atomic_write_json(self.state_path, state)
        return event

    def propose(
        self,
        agent: str,
        statement: str,
        *,
        evidence: Any | None = None,
    ) -> dict[str, Any]:
        peer = self._require_peer(agent)
        cleaned = " ".join(str(statement).split()).strip()
        if not cleaned:
            raise ValueError("statement must not be empty")
        decision_id = "decision-" + uuid.uuid4().hex
        proposal = self.publish(
            peer,
            "PLAN",
            {
                "decision_id": decision_id,
                "statement": cleaned,
                "state": "PROPOSED",
            },
            evidence=evidence,
        )
        with self._locked():
            state = self._load_state()
            state["decisions"][decision_id] = {
                "decision_id": decision_id,
                "statement": cleaned,
                "proposed_by": peer,
                "proposal_event_id": proposal["event_id"],
                "created_at": proposal["created_at"],
                "state": "PROPOSED",
                "votes": {},
            }
            state["revision"] = int(state.get("revision", 0)) + 1
            _atomic_write_json(self.state_path, state)
            return _json_copy(state["decisions"][decision_id])

    def vote(
        self,
        agent: str,
        decision_id: str,
        vote: str,
        *,
        evidence: Any | None = None,
    ) -> dict[str, Any]:
        peer = self._require_peer(agent)
        choice = str(vote).strip().upper()
        if choice not in _VOTES:
            raise ValueError(f"vote must be one of: {', '.join(sorted(_VOTES))}")

        with self._locked():
            state = self._load_state()
            if decision_id not in state["decisions"]:
                raise KeyError(f"unknown decision: {decision_id}")
            decision = state["decisions"][decision_id]
            decision["votes"][peer] = {
                "vote": choice,
                "evidence": _json_copy(evidence),
                "created_at": _utc_now(),
            }
            vote_values = {
                name: item["vote"] for name, item in decision["votes"].items()
            }
            if "DISSENT" in vote_values.values():
                decision["state"] = "CONTESTED"
            elif all(vote_values.get(peer_name) == "SUPPORT" for peer_name in _PEERS):
                decision["state"] = "QUORUM_REACHED"
            else:
                decision["state"] = "PENDING_PEER"

            event = {
                "schema": "uap-matrix/vote-event-v1",
                "event_id": "evt-" + uuid.uuid4().hex,
                "matrix_id": self.matrix_id,
                "decision_id": decision_id,
                "agent": peer,
                "peer_status": "PEER",
                "vote": choice,
                "evidence": _json_copy(evidence),
                "decision_state": decision["state"],
                "created_at": _utc_now(),
            }
            if choice == "DISSENT":
                state["blackboard"]["DISSENT"].append(event)
            state["revision"] = int(state.get("revision", 0)) + 1
            state["head_event_id"] = event["event_id"]
            self._write_event(event)
            _atomic_write_json(self.state_path, state)
            return _json_copy(decision)

    def checkpoint(self, label: str = "manual") -> dict[str, Any]:
        safe_label = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in label.strip()
        ).strip("-") or "manual"
        with self._locked():
            state = self._load_state()
            checkpoint_id = (
                "checkpoint-"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + "-"
                + uuid.uuid4().hex[:8]
            )
            payload = {
                "schema": "uap-matrix/checkpoint-v1",
                "checkpoint_id": checkpoint_id,
                "label": safe_label,
                "created_at": _utc_now(),
                "state": state,
            }
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            path = self.checkpoint_dir / f"{checkpoint_id}.json"
            _atomic_write_json(path, payload)
            return {
                "checkpoint_id": checkpoint_id,
                "label": safe_label,
                "path": str(path),
                "revision": state.get("revision", 0),
            }

    def rollback(self, checkpoint_id: str, *, authorized_by: str) -> dict[str, Any]:
        actor = str(authorized_by).strip()
        if not actor:
            raise ValueError("authorized_by is required")
        path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if not path.exists():
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")

        with self._locked():
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            restored = _json_copy(checkpoint["state"])
            event = {
                "schema": "uap-matrix/rollback-event-v1",
                "event_id": "evt-" + uuid.uuid4().hex,
                "matrix_id": self.matrix_id,
                "checkpoint_id": checkpoint_id,
                "authorized_by": actor,
                "scope": "LOCAL_SHARED_STATE_ONLY",
                "created_at": _utc_now(),
            }
            restored["revision"] = int(restored.get("revision", 0)) + 1
            restored["head_event_id"] = event["event_id"]
            self._write_event(event)
            _atomic_write_json(self.state_path, restored)
            return {
                "rolled_back": True,
                "checkpoint_id": checkpoint_id,
                "authorized_by": actor,
                "revision": restored["revision"],
                "external_actions_performed": False,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._locked():
            return _json_copy(self._load_state())

    def status(self) -> dict[str, Any]:
        state = self.snapshot()
        return {
            "uap_matrix": "ONLINE",
            "uap_expansion": state["uap_expansion"],
            "matrix_id": self.matrix_id,
            "hive_id": state["hive_id"],
            "mode": state["mode"],
            "peer_agents": list(_PEERS),
            "peer_symmetry": True,
            "revision": state["revision"],
            "head_event_id": state["head_event_id"],
            "decision_count": len(state["decisions"]),
            "blackboard_counts": {
                channel: len(items)
                for channel, items in state["blackboard"].items()
            },
            "human_authority": state["human_authority"],
            "execution_authority": state["execution_authority"],
            "state_dir": str(self.state_dir),
        }
