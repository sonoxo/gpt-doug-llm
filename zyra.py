"""Zyra: local policy guardrails for GPT Doug.

Zyra is a deterministic defense-in-depth layer, not a security boundary.
It inspects user input and model output, redacts common secrets, and records
privacy-preserving audit events without storing conversation content.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Verdict:
    allowed: bool
    text: str
    risk: str = "low"
    reasons: list[str] = field(default_factory=list)
    requires_approval: bool = False


class Zyra:
    """Fail-closed watchdog for terminal AI conversations."""

    SECRET_PATTERNS = (
        (re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b"), "API token"),
        (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
        (re.compile(r"(?i)\b(password|passwd|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]{6,}"), "credential"),
    )
    BLOCK_PATTERNS = (
        (re.compile(r"(?i)\brm\s+-rf\s+(?:/(?:\s|$)|~(?:/|\s|$)|\$HOME(?:/|\s|$))"), "destructive filesystem command"),
        (re.compile(r"(?i)\b(?:mkfs|dd\s+if=.*\s+of=/dev/|diskutil\s+erase)\b"), "disk destruction command"),
        (re.compile(r"(?i)\b(?:disable|bypass|evade)\b.{0,35}\b(?:security|authentication|firewall|guardrail)\b"), "security bypass request"),
        (re.compile(r"(?i)ignore (?:all |any )?(?:previous|prior|system) instructions"), "prompt-injection phrase"),
    )
    APPROVAL_PATTERNS = (
        (re.compile(r"(?i)\b(?:publish|deploy|push|send|email|purchase|buy|transfer|delete)\b"), "external or consequential action"),
        (re.compile(r"(?i)\b(?:curl|wget|ssh|scp)\b"), "network command"),
    )

    def __init__(self, audit_path: str | Path | None = None, event_sink=None):
        self.audit_path = Path(audit_path or Path.home() / ".gpt-doug" / "zyra-audit.jsonl")
        self.event_sink = event_sink

    def inspect(self, text: str, direction: str = "input") -> Verdict:
        if not isinstance(text, str) or len(text) > 100_000:
            verdict = Verdict(False, "", "critical", ["invalid or oversized message"])
            self._audit(direction, text if isinstance(text, str) else "", verdict)
            return verdict
        cleaned = text
        reasons: list[str] = []
        for pattern, label in self.SECRET_PATTERNS:
            cleaned, count = pattern.subn(f"[REDACTED {label.upper()}]", cleaned)
            if count:
                reasons.append(f"redacted {label}")
        blocked = [label for pattern, label in self.BLOCK_PATTERNS if pattern.search(cleaned)]
        approval = [label for pattern, label in self.APPROVAL_PATTERNS if pattern.search(cleaned)]
        if blocked:
            verdict = Verdict(False, cleaned, "critical", reasons + blocked)
        else:
            verdict = Verdict(True, cleaned, "medium" if approval or reasons else "low", reasons + approval, bool(approval))
        self._audit(direction, text, verdict)
        return verdict

    def _audit(self, direction: str, original: str, verdict: Verdict) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "allowed": verdict.allowed,
            "risk": verdict.risk,
            "reasons": verdict.reasons,
            "content_sha256": hashlib.sha256(original.encode(errors="replace")).hexdigest(),
        }
        try:
            self.audit_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")
            self.audit_path.chmod(0o600)
        except OSError:
            pass
        if self.event_sink:
            try:
                self.event_sink.emit(event)
            except Exception:
                # Foundry is supplemental: local enforcement never depends on
                # external availability and conversation content is not queued.
                pass

    def status(self) -> str:
        return f"Zyra active // audit: {self.audit_path} // fail-closed policy online"
