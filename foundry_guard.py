"""Optional outbound-only Palantir Foundry security event bridge."""

from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class FoundrySecuritySink:
    """Send redacted Zyra verdict metadata to an approved Foundry endpoint.

    The bridge is intentionally write-only and receives no commands. The exact
    endpoint must be provisioned by the Foundry administrator with least-
    privilege permissions for a security-event action or ingestion service.
    """

    endpoint: str
    token: str
    timeout: float = 3.0

    @classmethod
    def from_environment(cls) -> "FoundrySecuritySink | None":
        endpoint = os.getenv("FOUNDRY_SECURITY_ENDPOINT", "").strip()
        token = os.getenv("FOUNDRY_TOKEN", "").strip()
        if not endpoint and not token:
            return None
        if not endpoint or not token:
            raise ValueError("Both FOUNDRY_SECURITY_ENDPOINT and FOUNDRY_TOKEN are required")
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Foundry endpoint must use HTTPS")
        allowed_host = os.getenv("FOUNDRY_ALLOWED_HOST", parsed.hostname).strip().lower()
        if parsed.hostname.lower() != allowed_host:
            raise ValueError("Foundry endpoint host is not allowlisted")
        return cls(endpoint, token)

    def emit(self, event: dict) -> None:
        safe_event = {
            "timestamp": event["timestamp"],
            "direction": event["direction"],
            "allowed": event["allowed"],
            "risk": event["risk"],
            "reasons": event["reasons"],
            "source": "gpt-doug-zyra",
            "schema_version": 1,
        }
        request = urllib.request.Request(
            self.endpoint,
            json.dumps(safe_event).encode(),
            {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout, context=ssl.create_default_context()) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Foundry rejected security event: HTTP {response.status}")
