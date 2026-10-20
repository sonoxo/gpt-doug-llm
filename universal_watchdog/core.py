"""Model-agnostic policy engine with a human-reviewed RSI change gate."""
from __future__ import annotations

import re
import secrets
import hashlib
import threading
import time
from typing import Any

from .policy import (ACTIONS, CAPABILITY_PREFIXES, HEX_SHA256, NAME_PATTERN,
                     SAFE_DEFAULT_GRANTS, VALID_SCOPES, PolicyError,
                     judge, normalise_event, require_name)
from .store import IntegrityFailure, Store


class Watchtower:
    def __init__(self, database: str, audit_key: bytes, *, max_tokens: int = 50_000,
                 max_cost: float = 20.0, max_actions_per_minute: int = 100,
                 external_stop_checker=None):
        self.store = Store(database, audit_key)
        self.max_tokens = max_tokens
        self.max_cost = max_cost
        self.max_actions_per_minute = max_actions_per_minute
        self.external_stop_checker = external_stop_checker or self._repo_ai_stop
        self.lock = threading.RLock()
        self.recent = {}

    @staticmethod
    def _repo_ai_stop() -> dict:
        try:
            from ai_killswitch import status
        except ImportError:
            return {"stopped": False, "integrated": False, "reason": "not_installed"}
        result = status()
        return {"stopped": bool(result.get("stopped", True)), "integrated": True,
                "reason": result.get("reason", "unknown")}

    def register(self, raw: Any) -> dict:
        if not isinstance(raw, dict):
            raise PolicyError("model registration must be an object")
        fields = {x: require_name(raw, x) for x in ("model_id", "provider", "agent_id")}
        grants = raw.get("grants", SAFE_DEFAULT_GRANTS)
        scopes = raw.get("scopes", ["public"])
        if not isinstance(grants, list) or not grants or len(grants) > 50 or any(not isinstance(g, str) or g not in CAPABILITY_PREFIXES for g in grants):
            raise PolicyError("grants must be known capability identifiers")
        if not isinstance(scopes, list) or not scopes or any(s not in VALID_SCOPES for s in scopes):
            raise PolicyError("scopes invalid")
        ingest_token = secrets.token_urlsafe(36)
        model = {**fields, "grants": sorted(set(grants)), "scopes": sorted(set(scopes)),
                 "token_hash": hashlib.sha256(ingest_token.encode("utf-8")).hexdigest()}
        self.store.register_model(model)
        response = {k: v for k, v in model.items() if k != "token_hash"}
        return {**response, "ingest_token": ingest_token, "status": "registered",
                "enforcement": "cooperative_gateway", "secret_notice": "Copy this token now; only its hash is stored."}

    def external_status(self) -> dict:
        try:
            response = self.external_stop_checker()
            if not isinstance(response, dict) or not isinstance(response.get("stopped"), bool):
                raise ValueError("invalid external stop state")
            return response
        except Exception:
            return {"stopped": True, "reason": "external_stop_unreadable", "integrated": True}

    def _rate_check(self, model_id: str) -> bool:
        """Local in-memory per-model burst cap (multi-process deployments need shared rate control)."""
        now = time.monotonic()
        arr = self.recent.setdefault(model_id, [])
        arr[:] = [t for t in arr if t > now - 60]
        if len(arr) >= self.max_actions_per_minute:
            return False
        arr.append(now)
        return True

    def evaluate(self, raw: Any) -> dict:
        event = normalise_event(raw, content_key=self.store.key)
        with self.lock:
            self.store.assert_chain()
            stopped = self.store.stopped()["stopped"] or self.external_status()["stopped"]
            model = self.store.get_model(event["model_id"])
            verdict, reason, risk = judge(event, model, stopped=stopped,
                                          max_tokens=self.max_tokens, max_cost=self.max_cost)
            if model is not None and model["agent_id"] != event["agent_id"]:
                verdict, reason, risk = "deny", "agent_identity_mismatch", "high"
            if not stopped and verdict != "deny" and not self._rate_check(event["model_id"]):
                verdict, reason, risk = "deny", "event_rate_limit_exceeded", "high"
            approval_id = event["approval_id"]
            if verdict == "review" and approval_id:
                if self.store.consume_approval(approval_id, event["event_digest"]):
                    verdict, reason, risk = "allow", "human_approval_consumed", "high"
                else:
                    verdict, reason, risk = "deny", "invalid_expired_or_consumed_approval", "high"
            elif verdict == "allow" and approval_id:
                verdict, reason, risk = "deny", "unexpected_approval_token", "high"
            decision = self.store.store_decision(event, verdict, reason, risk, approval_id if verdict == "allow" else "")
            return {"schema": "xunia.watchtower.decision.v1", "id": decision["decision_id"],
                    "verdict": verdict, "enforce": verdict == "allow", "reason": reason, "risk": risk,
                    "event_digest": event["event_digest"], "model_id": event["model_id"],
                    "trace_id": event["trace_id"], "requires_operator_review": verdict == "review"}

    def approve(self, decision_id: str, review_evidence_sha: str, ttl: int = 600) -> dict:
        if not isinstance(decision_id, str) or not re.fullmatch(r"[a-f0-9]{32}", decision_id):
            raise PolicyError("decision_id must be a 32-character hex id")
        if not isinstance(review_evidence_sha, str) or not HEX_SHA256.fullmatch(review_evidence_sha):
            raise PolicyError("operator review evidence SHA-256 required")
        if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl < 30 or ttl > 3600:
            raise PolicyError("ttl must be 30..3600 seconds")
        with self.lock:
            self.store.assert_chain()
            if self.store.stopped()["stopped"] or self.external_status()["stopped"]:
                raise PermissionError("operator_stop_active")
            return self.store.approve(decision_id, review_evidence_sha, ttl)

    def stop(self, reason: str) -> dict:
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 100:
            raise PolicyError("stop reason required, max 100")
        with self.lock:
            self.store.set_stop(True, reason.strip())
            return self.store.stopped()

    def rearm(self, confirmation: str) -> dict:
        if confirmation != "REARM WATCHTOWER":
            raise PermissionError("operator confirmation mismatch")
        with self.lock:
            if self.external_status()["stopped"]:
                raise PermissionError("external_ai_stop_active")
            self.store.set_stop(False, "operator_confirmed_rearm")
            return self.store.stopped()

    def ontology(self) -> dict:
        """Grounded graph: report only registered/observed connected model identities."""
        items = self.store.list_models()
        root = {"id": "xunia-watchtower", "type": "oversight_gateway", "status": "operator_local"}
        nodes = [root] + [
            {"id": "model:" + m["model_id"], "type": "registered_model",
             "provider": m["provider"], "agent_id": m["agent_id"],
             "status": "registered_not_necessarily_online",
             "grants": m["grants"], "scopes": m["scopes"]} for m in items
        ]
        edges = [{"source": n["id"], "target": root["id"],
                  "relationship": "requires_approval_before_action"} for n in nodes[1:]]
        return {"schema": "xunia.watchtower.ontology.v1", "mode": "registered_models_only",
                "nodes": nodes, "edges": edges,
                "caveat": "Registration and last_seen do not prove continuous coverage."}

    def overview(self) -> dict:
        with self.lock:
            integrity = self.store.verify_chain()
            switch = self.store.stopped()
            external = self.external_status()
            return {"schema": "xunia.watchtower.overview.v1", "mode": "local_governed",
                    "stop": {"stopped": switch["stopped"] or external["stopped"],
                             "local": switch, "existing_gpt_doug_gate": external},
                    "audit": integrity, "stats": self.store.counts(),
                    "models": self.store.list_models(),
                    "limitations": ["Only registered and instrumented models are monitored.",
                                    "Public museum is demonstration-only; no live provider keys."]}
