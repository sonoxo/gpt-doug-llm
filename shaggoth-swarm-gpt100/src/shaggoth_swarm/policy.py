from __future__ import annotations

import os
from dataclasses import dataclass, field

from .capabilities import ALL_SUPPORTED_CAPABILITIES, PROFILES, PROFILE_REASONING


DEFAULT_ALLOWED_CAPABILITIES = PROFILE_REASONING


def _parse_csv(raw: str) -> frozenset[str]:
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


@dataclass(slots=True)
class CapabilityPolicy:
    allowed: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_CAPABILITIES)
    scopes: dict[str, frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = self.allowed - ALL_SUPPORTED_CAPABILITIES
        if unknown:
            raise ValueError(f"unknown capabilities: {', '.join(sorted(unknown))}")

    @classmethod
    def from_env(cls) -> "CapabilityPolicy":
        profile = os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning")
        if profile not in PROFILES:
            raise ValueError(f"unknown capability profile: {profile}")
        allowed = set(PROFILES[profile])
        allowed.update(_parse_csv(os.getenv("SHAGGOTH_EXTRA_CAPABILITIES", "")))
        denied = _parse_csv(os.getenv("SHAGGOTH_DENY_CAPABILITIES", ""))
        allowed.difference_update(denied)
        return cls(allowed=frozenset(allowed))

    def check(self, required: frozenset[str]) -> tuple[bool, frozenset[str]]:
        missing = required - self.allowed
        return not missing, missing

    def require(self, required: frozenset[str]) -> None:
        ok, missing = self.check(required)
        if not ok:
            raise PermissionError(f"capabilities denied: {', '.join(sorted(missing))}")

    def grant_scope(self, capability: str, values: frozenset[str]) -> None:
        if capability not in self.allowed:
            raise PermissionError(f"capability is not enabled: {capability}")
        self.scopes[capability] = values

    def require_scope(self, capability: str, value: str) -> None:
        self.require(frozenset({capability}))
        values = self.scopes.get(capability, frozenset())
        if value not in values:
            raise PermissionError(f"scope denied for {capability}: {value}")
