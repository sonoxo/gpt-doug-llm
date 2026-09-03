"""Authorized Palantir Gotham REST adapter.

Gotham's public API is OAuth2/Bearer authenticated and lives under
/api/gotham/v1. This module reuses the hardened HTTPS/host-pinned transport
from FoundryClient while keeping Gotham credentials separately configured.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Any, Optional

from palantir_foundry import FoundryClient, FoundryConfigurationError


class PalantirGothamClient:
    def __init__(self, transport: FoundryClient) -> None:
        self.transport = transport

    @classmethod
    def from_environment(cls) -> Optional["PalantirGothamClient"]:
        base_url = os.getenv("GOTHAM_BASE_URL", "").strip()
        token = os.getenv("GOTHAM_TOKEN", "").strip()
        client_id = os.getenv("GOTHAM_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOTHAM_CLIENT_SECRET", "").strip()
        if not base_url:
            return None
        if not token and not (client_id and client_secret):
            raise FoundryConfigurationError(
                "Configure GOTHAM_TOKEN or both GOTHAM_CLIENT_ID and GOTHAM_CLIENT_SECRET"
            )
        return cls(
            FoundryClient(
                base_url=base_url,
                static_token=token,
                client_id=client_id,
                client_secret=client_secret,
                scopes=os.getenv("GOTHAM_SCOPES", "").strip(),
                allowed_host=os.getenv("GOTHAM_ALLOWED_HOST", "").strip(),
                writes_enabled=os.getenv("GOTHAM_ENABLE_WRITES", "").strip().lower()
                in {"1", "true", "yes", "on"},
            )
        )

    def status(self) -> dict[str, Any]:
        status = self.transport.status()
        status["platform"] = "gotham"
        status["api"] = "/api/gotham/v1"
        return status

    def get_object(self, primary_key: str) -> dict[str, Any]:
        key = urllib.parse.quote(primary_key, safe="")
        return self.transport.request("GET", f"/api/gotham/v1/objects/{key}")

    def create_object(self, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        object_type_q = urllib.parse.quote(object_type, safe="")
        return self.transport.request(
            "POST",
            f"/api/gotham/v1/objects/types/{object_type_q}",
            body=payload,
            write=True,
        )

    def openapi(self) -> dict[str, Any]:
        return self.transport.request("GET", "/api/gotham/openapi")
