"""Deterministic, provider-neutral pre-action policy decisions.

The gate inspects normalized intents; it does not claim to reliably classify every
prompt or to monitor external providers without instrumentation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from typing import Any


class PolicyError(ValueError):
    """Malformed/unacceptable guard request."""


ACTIONS = {
    "inference": frozenset({"chat", "generate", "embed"}),
    "retrieval": frozenset({"read_public", "read_internal"}),
    "telemetry": frozenset({"heartbeat", "observe"}),
    "tool_call": frozenset({"read", "write", "execute", "network", "administer"}),
    "model_update": frozenset({"weights", "fine_tune", "architecture", "self_modify"}),
    "training": frozenset({"start", "dataset_change", "checkpoint_promote"}),
    "deployment": frozenset({"stage", "promote", "rollback"}),
    "policy_change": frozenset({"propose", "activate"}),
}
HIGH_IMPACT = {
    ("tool_call", "write"), ("tool_call", "execute"),
    ("tool_call", "network"), ("tool_call", "administer"),
    ("model_update", "weights"), ("model_update", "fine_tune"),
    ("model_update", "architecture"), ("model_update", "self_modify"),
    ("training", "start"), ("training", "dataset_change"),
    ("training", "checkpoint_promote"), ("deployment", "promote"),
    ("deployment", "rollback"), ("policy_change", "activate"),
}
SELF_MODIFYING_KINDS = {"model_update", "training", "policy_change", "deployment"}
CAPABILITY_PREFIXES = frozenset({f"{kind}:{act}" for kind, acts in ACTIONS.items() for act in acts})
SAFE_DEFAULT_GRANTS = ["inference:chat", "inference:generate", "inference:embed", "telemetry:heartbeat"]
VALID_SCOPES = frozenset({"public", "internal", "restricted"})
VALID_TRUST = frozenset({"trusted", "untrusted"})
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:/@+-]{0,119}$")
HEX_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
INJECTION_PATTERNS = (
    re.compile(r"\bignore (?:all |any )?(?:previous|prior|system|developer) instructions\b", re.I),
    re.compile(r"\b(?:override|disable|bypass) (?:the )?(?:safety|policy|guardrails|system prompt)\b", re.I),
)


def require_string(obj: dict, key: str, maximum: int, allow_empty: bool = False) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise PolicyError(f"{key}: expected non-empty string (max {maximum})")
    if any(ord(c) < 32 for c in value if c not in "\t\n"):
        raise PolicyError(f"{key}: invalid control character")
    return value.strip()


def require_name(obj: dict, key: str) -> str:
    value = require_string(obj, key, 120)
    if not NAME_PATTERN.fullmatch(value):
        raise PolicyError(f"{key}: invalid identifier")
    return value


def normalise_event(raw: Any, *, content_key: bytes | None = None) -> dict:
    if not isinstance(raw, dict):
        raise PolicyError("event must be a JSON object")
    model_id = require_name(raw, "model_id")
    provider = require_name(raw, "provider")
    agent_id = require_name(raw, "agent_id")
    kind = require_string(raw, "kind", 32)
    action = require_string(raw, "action", 32)
    if kind not in ACTIONS or action not in ACTIONS[kind]:
        raise PolicyError("unknown kind or action: fail closed")
    scope = raw.get("scope", "public")
    if scope not in VALID_SCOPES:
        raise PolicyError("invalid scope")
    source_trust = raw.get("source_trust", "trusted")
    if source_trust not in VALID_TRUST:
        raise PolicyError("invalid source_trust")
    content = raw.get("content", "")
    if not isinstance(content, str) or len(content) > 16000:
        raise PolicyError("content must be a string <= 16000 characters")
    resource = raw.get("resource", "unspecified")
    if not isinstance(resource, str) or len(resource) > 120 or not NAME_PATTERN.fullmatch(resource):
        raise PolicyError("resource must be a non-sensitive identifier")
    trace_id = raw.get("trace_id", "")
    if not isinstance(trace_id, str) or len(trace_id) > 128 or (trace_id and not NAME_PATTERN.fullmatch(trace_id)):
        raise PolicyError("trace_id must be a string <= 128 characters")
    tokens = raw.get("estimated_tokens", 0)
    if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0 or tokens > 1_000_000_000:
        raise PolicyError("estimated_tokens invalid")
    cost = raw.get("estimated_cost_usd", 0)
    if isinstance(cost, bool) or not isinstance(cost, (float, int)) or not 0 <= cost <= 1_000_000:
        raise PolicyError("estimated_cost_usd invalid")
    attested_test_sha256 = raw.get("test_report_sha256", "")
    if attested_test_sha256 and (not isinstance(attested_test_sha256, str) or not HEX_SHA256.fullmatch(attested_test_sha256)):
        raise PolicyError("test_report_sha256 must be a SHA-256 hexadecimal digest")
    rollback_ref = raw.get("rollback_ref", "")
    if rollback_ref and (not isinstance(rollback_ref, str) or len(rollback_ref) > 128):
        raise PolicyError("rollback_ref invalid")
    fingerprint = (hmac.new(content_key, content.encode("utf-8"), hashlib.sha256).hexdigest()
                   if content_key else hashlib.sha256(content.encode("utf-8")).hexdigest())
    cleaned = {
        "model_id": model_id, "provider": provider, "agent_id": agent_id,
        "kind": kind, "action": action, "scope": scope,
        "source_trust": source_trust, "resource": resource.strip(),
        "content_sha256": fingerprint,
        "content_length": len(content), "estimated_tokens": tokens,
        "estimated_cost_usd": round(float(cost), 6),
        "test_report_sha256": attested_test_sha256, "rollback_ref": rollback_ref,
    }
    canon = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
    cleaned["event_digest"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    cleaned["trace_id"] = trace_id
    cleaned["_content"] = content
    cleaned["approval_id"] = raw.get("approval_id", "")
    if not isinstance(cleaned["approval_id"], str) or len(cleaned["approval_id"]) > 80:
        raise PolicyError("approval_id invalid")
    return cleaned


def judge(event: dict, model: dict | None, *, stopped: bool, max_tokens: int = 50000,
          max_cost: float = 20.0) -> tuple[str, str, str]:
    """Return outcome/reason/risk. Overrides can only approve REVIEW, not DENY."""
    if stopped:
        return "deny", "operator_emergency_stop", "critical"
    if model is None:
        return "deny", "unregistered_model", "high"
    if model.get("provider") != event["provider"]:
        return "deny", "provider_identity_mismatch", "high"
    if event["scope"] not in model["scopes"]:
        return "deny", "data_scope_not_granted", "high"
    capability = event["kind"] + ":" + event["action"]
    if capability not in model["grants"]:
        return "deny", "capability_not_granted", "high"
    if event["estimated_tokens"] > max_tokens:
        return "deny", "token_budget_exceeded", "high"
    if event["estimated_cost_usd"] > max_cost:
        return "deny", "cost_budget_exceeded", "high"
    c = unicodedata.normalize("NFKC", event["_content"])
    if any(p.search(c) for p in SECRET_PATTERNS):
        return "deny", "credential_or_private_key_pattern", "critical"
    if event["source_trust"] == "untrusted" and any(p.search(c) for p in INJECTION_PATTERNS):
        return "review", "untrusted_instruction_override_pattern", "high"
    if (event["kind"], event["action"]) in HIGH_IMPACT:
        if event["kind"] in SELF_MODIFYING_KINDS and (not event["test_report_sha256"] or not event["rollback_ref"]):
            return "deny", "rsi_evidence_and_rollback_required", "critical"
        return "review", "human_approval_required", "high"
    return "allow", "within_registered_policy", "low"
