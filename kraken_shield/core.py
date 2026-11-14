"""Kraken Shield CL1: bounded local-first defensive decision and audit plane.

This module assesses requests; it does not execute commands, modify repositories,
make cloud API calls, or authorize physical actions. The audit hash chain can
detect modified existing entries, but cannot prove that entries were not deleted.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.cl1_free_policy import is_local_inference_url, is_local_ollama_model
from ai_killswitch import status as stop_status

_MAX_TEXT = 16_384
_MAX_AUDIT = 16 * 1024 * 1024
_ZERO = "0" * 64
_LOCAL_CAPABILITIES = frozenset({"inspect", "status", "local_report", "ontology_read"})
_LOCK = threading.RLock()


class KrakenShieldError(RuntimeError):
    """Fail-closed configuration or audit error."""


def _canonical(item: dict[str, Any]) -> bytes:
    return json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _verify_entries(lines: list[str]) -> tuple[int, str]:
    prev = _ZERO
    for index, line in enumerate(lines):
        if not line.endswith("\n"):
            raise KrakenShieldError("audit_incomplete_record")
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("not an object")
            digest = item.pop("digest")
            if item.get("sequence") != index + 1 or item.get("previous") != prev:
                raise ValueError("broken chain")
            expected = hashlib.sha256(_canonical(item)).hexdigest()
            if digest != expected:
                raise ValueError("digest mismatch")
            prev = digest
        except (ValueError, TypeError, KeyError) as exc:
            raise KrakenShieldError("audit_integrity_failure") from exc
    return len(lines), prev


def _state_directory(configured: str | Path | None) -> Path:
    raw = str(configured or os.getenv("KRAKEN_SHIELD_STATE_DIR", "~/.gpt-doug/kraken-shield"))
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise KrakenShieldError("audit_directory_must_be_absolute")
    return path


class KrakenShield:
    """Assessment-only overlay on the existing Golden Shield and AI stop gate."""

    def __init__(self, *, state_dir: str | Path | None = None, shield: Any = None):
        self.state_dir = _state_directory(state_dir)
        self.audit_path = self.state_dir / "decisions.jsonl"
        self._shield = shield

    def _safe_dir(self, *, create: bool) -> bool:
        if create:
            self.state_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        try:
            info = self.state_dir.lstat()
        except FileNotFoundError:
            return False
        if not stat.S_ISDIR(info.st_mode) or (stat.S_IMODE(info.st_mode) & 0o077):
            raise KrakenShieldError("unsafe_audit_directory")
        return True

    def _open_audit(self, flags: int) -> int:
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.audit_path, flags | nofollow, 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (stat.S_IMODE(info.st_mode) & 0o077):
            os.close(fd)
            raise KrakenShieldError("unsafe_audit_file")
        return fd

    def verify_audit(self) -> dict[str, Any]:
        """Read-only integrity check; a missing history starts empty."""
        try:
            if not self._safe_dir(create=False):
                return {"valid": True, "events": 0, "head": _ZERO}
            try:
                fd = self._open_audit(os.O_RDONLY)
            except FileNotFoundError:
                return {"valid": True, "events": 0, "head": _ZERO}
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
                if os.fstat(stream.fileno()).st_size > _MAX_AUDIT:
                    raise KrakenShieldError("audit_size_limit")
                count, head = _verify_entries(stream.readlines())
                return {"valid": True, "events": count, "head": head}
        except (OSError, UnicodeError, KrakenShieldError):
            return {"valid": False, "events": None, "head": None}

    def _append(self, decision: str, reason: str, fingerprint: str) -> str:
        """Append without following symlinks; refuse a corrupt or full log."""
        try:
            with _LOCK:
                self._safe_dir(create=True)
                fd = self._open_audit(os.O_CREAT | os.O_RDWR)
                with os.fdopen(fd, "r+", encoding="utf-8") as stream:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                    if os.fstat(stream.fileno()).st_size > _MAX_AUDIT - 2048:
                        raise KrakenShieldError("audit_size_limit")
                    count, previous = _verify_entries(stream.readlines())
                    event = {
                        "schema": "kraken-shield/audit-v1",
                        "sequence": count + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "decision": decision,
                        "reason_code": reason,
                        "fingerprint": fingerprint,
                        "previous": previous,
                    }
                    digest = hashlib.sha256(_canonical(event)).hexdigest()
                    stream.seek(0, os.SEEK_END)
                    stream.write(json.dumps({**event, "digest": digest}, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                    return digest
        except (OSError, UnicodeError, KrakenShieldError) as exc:
            raise KrakenShieldError("audit_write_unavailable") from exc

    def policy(self) -> dict[str, Any]:
        provider = os.getenv("GPT_DOUG_PROVIDER", "none").strip().lower()
        url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
        if provider not in {"ollama", "none"}:
            return {"allowed": False, "reason": "nonlocal_provider", "provider": provider}
        if not is_local_inference_url(url):
            return {"allowed": False, "reason": "nonlocal_endpoint", "provider": provider}
        if not is_local_ollama_model(model):
            return {"allowed": False, "reason": "cloud_model_blocked", "provider": provider}
        return {"allowed": True, "reason": "local_only", "provider": provider}

    def status(self) -> dict[str, Any]:
        stop = stop_status()
        policy = self.policy()
        audit = self.verify_audit()
        ready = bool(not stop["stopped"] and policy["allowed"] and audit["valid"])
        return {
            "schema": "kraken-shield/status-v1",
            "name": "KRAKEN SHIELD / CL1",
            "ready": ready,
            "mode": "LOCAL_ONLY_DEFENSIVE",
            "paid_services_allowed": False,
            "autonomous_execution": False,
            "emergency_stop": {"stopped": bool(stop["stopped"]), "reason": stop["reason"]},
            "provider_policy": policy,
            "audit": audit,
            "layers": ["CL1", "AI_STOP", "GOLDEN_SHIELD", "ZYRA", "HASH_CHAIN_AUDIT"],
        }

    def _golden(self):
        if self._shield is None:
            from golden_shield import GoldenShield
            self._shield = GoldenShield()
        return self._shield

    def inspect(self, text: str, *, source: str = "local") -> dict[str, Any]:
        """Do not allow a request unless stop, CL1, Golden Shield and audit pass."""
        if not isinstance(text, str):
            raise ValueError("request_must_be_text")
        fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        policy = self.policy()
        stop = stop_status()
        if stop["stopped"]:
            decision, reason = "BLOCK", "operator_stop"
        elif not policy["allowed"]:
            decision, reason = "BLOCK", policy["reason"]
        elif not text.strip() or len(text.encode("utf-8")) > _MAX_TEXT:
            decision, reason = "BLOCK", "invalid_request_size"
        else:
            try:
                assessment = self._golden().inspect_inbound(text, source=source)
                decision = "ALLOW" if assessment.action == "ALLOW" else "BLOCK"
                reason = "golden_shield_allow" if decision == "ALLOW" else "golden_shield_reject"
            except Exception:
                decision, reason = "BLOCK", "golden_shield_unavailable"
        digest = self._append(decision, reason, fingerprint)
        return {
            "schema": "kraken-shield/decision-v1",
            "decision": decision,
            "reason_code": reason,
            "fingerprint": fingerprint,
            "audit_digest": digest,
            "executed": False,
        }

    def check_capability(self, capability: str) -> dict[str, Any]:
        """Advisory gate only. Even ALLOW does not execute a requested action."""
        if not isinstance(capability, str):
            raise ValueError("capability_must_be_text")
        capability = capability.strip().lower()
        fingerprint = hashlib.sha256(capability.encode("utf-8")).hexdigest()
        stop = stop_status()
        policy = self.policy()
        if stop["stopped"]:
            decision, reason = "BLOCK", "operator_stop"
        elif not policy["allowed"]:
            decision, reason = "BLOCK", policy["reason"]
        elif capability in _LOCAL_CAPABILITIES:
            decision, reason = "ALLOW", "read_only_capability"
        else:
            decision, reason = "BLOCK", "operator_approval_required"
        digest = self._append(decision, reason, fingerprint)
        return {
            "schema": "kraken-shield/capability-v1",
            "capability": capability[:64],
            "decision": decision,
            "reason_code": reason,
            "audit_digest": digest,
            "executed": False,
        }
