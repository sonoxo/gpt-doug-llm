from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_ALLOWED_CAPABILITIES = frozenset({"reason", "summarize", "classify", "plan"})


@dataclass(slots=True)
class CapabilityPolicy:
    allowed: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_CAPABILITIES)

    def check(self, required: frozenset[str]) -> tuple[bool, frozenset[str]]:
        missing = required - self.allowed
        return not missing, missing

    def require(self, required: frozenset[str]) -> None:
        ok, missing = self.check(required)
        if not ok:
            raise PermissionError(f"capabilities denied: {', '.join(sorted(missing))}")
