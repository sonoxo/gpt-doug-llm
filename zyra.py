"""Zyra: local policy guardrails for GPT Doug.

Zyra is a deterministic defense-in-depth layer, not a security boundary.
It inspects user input and model output, redacts common secrets, and records
privacy-preserving audit events without storing conversation content.
"""

from __future__ import annotations

import hashlib
import json
import re
import hmac
import fcntl
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from security_text import normalize_security_text


@dataclass
class Verdict:
    allowed: bool
    text: str
    risk: str = "low"
    reasons: list[str] = field(default_factory=list)
    requires_approval: bool = False
    control_ids: list[str] = field(default_factory=list)


class Zyra:
    """Fail-closed watchdog for terminal AI conversations."""

    POLICY_VERSION = "ZYRA/2.0"
    VALID_DIRECTIONS = frozenset({"input", "output", "control"})

    SECRET_PATTERNS = (
        (re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b"), "API token"),
        (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
        (re.compile(r"(?i)\b(password|passwd|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]{6,}"), "credential"),
    )
    BLOCK_PATTERNS = (
        (re.compile(r"(?i)\brm\s+(?:-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)|-r\s+-f|-f\s+-r)\s+(?:/(?:\s|$)|~(?:/|\s|$)|\$home(?:/|\s|$))"), "destructive filesystem command"),
        (re.compile(r"(?i)\b(?:mkfs|dd\s+if=.*\s+of=/dev/|diskutil\s+erase)\b"), "disk destruction command"),
        (re.compile(r"(?i)\b(?:disable|bypass|evade)\b.{0,35}\b(?:security|authentication|firewall|guardrail)\b"), "security bypass request"),
        (re.compile(r"(?i)ignore\s+(?:all\s+|any\s+)?(?:previous|prior|system)\s+instructions"), "prompt-injection phrase"),
        (re.compile(r"(?i)\b(?:wipe|erase|destroy)\b.{0,35}\b(?:root|entire filesystem|system disk)\b"), "destructive filesystem intent"),
    )
    APPROVAL_PATTERNS = (
        (re.compile(r"(?i)\b(?:publish|deploy|push|send|email|purchase|buy|transfer|delete)\b"), "external or consequential action"),
        (re.compile(r"(?i)\b(?:curl|wget|ssh|scp)\b"), "network command"),
    )

    def __init__(self, audit_path: str | Path | None = None, event_sink=None, audit_key: bytes | None = None, strict_audit: bool | None = None):
        self.audit_path = Path(audit_path or Path.home() / ".gpt-doug" / "zyra-audit.jsonl")
        self.event_sink = event_sink
        self.audit_key = audit_key
        self.strict_audit = bool(audit_key) if strict_audit is None else strict_audit
        if self.strict_audit and not self.audit_key:
            raise ValueError("strict audit mode requires an HMAC key")
        self.sink_failures = 0
        self._previous_mac = "GENESIS"
        if self.audit_key and self.audit_path.exists() and self.audit_path.stat().st_size:
            self._previous_mac = self.verify_audit_chain()

    def inspect(self, text: str, direction: str = "input") -> Verdict:
        if direction not in self.VALID_DIRECTIONS:
            raise ValueError("invalid audit direction")
        if not isinstance(text, str) or len(text) > 100_000:
            verdict = Verdict(False, "", "critical", ["invalid or oversized message"], control_ids=["ZYRA-INPUT-001"])
            self._audit(direction, text if isinstance(text, str) else "", verdict)
            return verdict
        cleaned = normalize_security_text(text)
        reasons: list[str] = []
        for pattern, label in self.SECRET_PATTERNS:
            cleaned, count = pattern.subn(f"[REDACTED {label.upper()}]", cleaned)
            if count:
                reasons.append(f"redacted {label}")
        blocked = [label for pattern, label in self.BLOCK_PATTERNS if pattern.search(cleaned)]
        approval = [label for pattern, label in self.APPROVAL_PATTERNS if pattern.search(cleaned)]
        if blocked:
            verdict = Verdict(False, cleaned, "critical", reasons + blocked, control_ids=["ZYRA-POLICY-001"])
        else:
            controls = (["ZYRA-DLP-001"] if reasons else []) + (["ZYRA-HITL-001"] if approval else [])
            verdict = Verdict(True, cleaned, "medium" if approval or reasons else "low", reasons + approval, bool(approval), controls)
        self._audit(direction, text, verdict)
        return verdict

    def _audit(self, direction: str, original: str, verdict: Verdict) -> None:
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_version": self.POLICY_VERSION,
            "direction": direction,
            "allowed": verdict.allowed,
            "risk": verdict.risk,
            "reasons": verdict.reasons,
            "control_ids": verdict.control_ids,
            "content_sha256": hashlib.sha256(original.encode(errors="replace")).hexdigest(),
        }
        if self.audit_key:
            event["previous_hmac"] = self._previous_mac
            canonical = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
            event["hmac_sha256"] = hmac.new(self.audit_key, canonical, hashlib.sha256).hexdigest()
            self._previous_mac = event["hmac_sha256"]
        try:
            self.audit_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.write(json.dumps(event) + "\n")
                handle.flush()
                self.audit_path.chmod(0o600)
        except OSError as error:
            if self.strict_audit:
                raise RuntimeError("Zyra audit write failed; request denied") from error
        if self.event_sink:
            try:
                self.event_sink.emit(event)
            except Exception:
                # Foundry is supplemental: local enforcement never depends on
                # external availability and conversation content is not queued.
                self.sink_failures += 1

    def status(self) -> str:
        return f"Zyra active // policy: {self.POLICY_VERSION} // audit: {self.audit_path} // sink failures: {self.sink_failures} // fail-closed policy online"

    def review_report(self) -> dict:
        """Return content-free evidence suitable for a security review."""
        final_hmac = self.verify_audit_chain() if self.audit_key and self.audit_path.exists() else None
        events = []
        if self.audit_path.exists():
            for line in self.audit_path.read_text(encoding="utf-8").splitlines():
                events.append(json.loads(line))
        mode = self.audit_path.stat().st_mode & 0o777 if self.audit_path.exists() else None
        controls = sorted({control for event in events for control in event.get("control_ids", [])})
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy_version": self.POLICY_VERSION,
            "audit_integrity": "verified" if final_hmac else "no-events",
            "audit_hmac_enabled": bool(self.audit_key),
            "audit_owner_only": mode in {None, 0o600},
            "event_count": len(events),
            "blocked_count": sum(not event.get("allowed", False) for event in events),
            "approval_count": sum("ZYRA-HITL-001" in event.get("control_ids", []) for event in events),
            "sink_failures": self.sink_failures,
            "controls_observed": controls,
        }

    def verify_audit_chain(self) -> str:
        previous = "GENESIS"
        for line_number, line in enumerate(self.audit_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
                claimed = event.pop("hmac_sha256")
            except (json.JSONDecodeError, KeyError) as error:
                raise ValueError(f"audit integrity failure at line {line_number}") from error
            if event.get("previous_hmac") != previous:
                raise ValueError(f"audit chain discontinuity at line {line_number}")
            canonical = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
            expected = hmac.new(self.audit_key, canonical, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(claimed, expected):
                raise ValueError(f"audit signature mismatch at line {line_number}")
            previous = claimed
        return previous
