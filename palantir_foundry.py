"""Palantir Foundry REST client for GPT-DOUG-LLM.

The client uses Foundry's documented OAuth2 client-credentials flow or an
explicit pre-issued bearer token. It only calls the configured Foundry host,
keeps writes disabled by default, and never stores credentials in the repo.
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional


class FoundryError(RuntimeError):
    """Base error raised by the Foundry client."""


class FoundryConfigurationError(FoundryError):
    """Raised when Foundry configuration is missing or unsafe."""


class FoundryWriteDisabled(FoundryError):
    """Raised when a write is attempted while writes are disabled."""


@dataclass
class FoundryClient:
    base_url: str
    client_id: str = ""
    client_secret: str = ""
    static_token: str = ""
    scopes: str = "api:ontologies-read"
    allowed_host: str = ""
    timeout: float = 10.0
    writes_enabled: bool = False
    _access_token: str = field(default="", init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise FoundryConfigurationError("FOUNDRY_BASE_URL must be an HTTPS Foundry URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise FoundryConfigurationError("FOUNDRY_BASE_URL must not contain credentials, query, or fragment")
        configured_host = (self.allowed_host or parsed.hostname).strip().lower()
        if parsed.hostname.lower() != configured_host:
            raise FoundryConfigurationError("Foundry base URL host is not allowlisted")
        self.allowed_host = configured_host
        if not self.static_token and not (self.client_id and self.client_secret):
            raise FoundryConfigurationError(
                "Configure FOUNDRY_TOKEN or both FOUNDRY_CLIENT_ID and FOUNDRY_CLIENT_SECRET"
            )

    @classmethod
    def from_environment(cls) -> Optional["FoundryClient"]:
        base_url = os.getenv("FOUNDRY_BASE_URL", "").strip()
        client_id = os.getenv("FOUNDRY_CLIENT_ID", "").strip()
        client_secret = os.getenv("FOUNDRY_CLIENT_SECRET", "").strip()
        token = os.getenv("FOUNDRY_TOKEN", "").strip()

        if not base_url:
            if client_id or client_secret:
                raise FoundryConfigurationError(
                    "FOUNDRY_BASE_URL is required with Foundry OAuth credentials"
                )
            return None

        raw_timeout = os.getenv("FOUNDRY_TIMEOUT_SECONDS", "10").strip()
        try:
            timeout = max(1.0, float(raw_timeout))
        except ValueError as error:
            raise FoundryConfigurationError("FOUNDRY_TIMEOUT_SECONDS must be a number") from error

        writes_enabled = os.getenv("FOUNDRY_ENABLE_WRITES", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        return cls(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            static_token=token,
            scopes=os.getenv("FOUNDRY_SCOPES", "api:ontologies-read").strip(),
            allowed_host=os.getenv("FOUNDRY_ALLOWED_HOST", "").strip(),
            timeout=timeout,
            writes_enabled=writes_enabled,
        )

    @property
    def host(self) -> str:
        return self.allowed_host

    def _token(self) -> str:
        if self.static_token:
            return self.static_token
        now = time.time()
        if self._access_token and now < self._token_expires_at - 30:
            return self._access_token

        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scopes:
            form["scope"] = self.scopes

        request = urllib.request.Request(
            f"{self.base_url}/multipass/api/oauth2/token",
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        payload = self._open_json(request)
        token = str(payload.get("access_token", ""))
        if not token:
            raise FoundryError("Foundry OAuth response did not include access_token")
        expires_in = max(60, int(payload.get("expires_in", 3600)))
        self._access_token = token
        self._token_expires_at = now + expires_in
        return token

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=ssl.create_default_context(),
            ) as response:
                body = response.read()
                if not 200 <= response.status < 300:
                    raise FoundryError(f"Foundry returned HTTP {response.status}")
                if not body:
                    return {}
                decoded = json.loads(body.decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise FoundryError("Foundry response was not a JSON object")
                return decoded
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8")[:1000]
            except Exception:
                detail = ""
            suffix = f": {detail}" if detail else ""
            raise FoundryError(f"Foundry returned HTTP {error.code}{suffix}") from error
        except urllib.error.URLError as error:
            raise FoundryError(f"Unable to reach Foundry: {error.reason}") from error
        except ValueError as error:
            raise FoundryError(f"Invalid Foundry response: {error}") from error

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict[str, Any]] = None,
        query: Optional[dict[str, Any]] = None,
        write: bool = False,
    ) -> dict[str, Any]:
        method = method.upper().strip()
        if not path.startswith("/") or "://" in path:
            raise FoundryConfigurationError("Foundry request path must be relative to the configured host")
        if write and not self.writes_enabled:
            raise FoundryWriteDisabled("Foundry writes are disabled; set FOUNDRY_ENABLE_WRITES=true explicitly")

        url = f"{self.base_url}{path}"
        if query:
            clean_query = {key: value for key, value in query.items() if value is not None}
            if clean_query:
                url += "?" + urllib.parse.urlencode(clean_query, doseq=True)

        parsed = urllib.parse.urlparse(url)
        if parsed.hostname is None or parsed.hostname.lower() != self.allowed_host:
            raise FoundryConfigurationError("Refusing request outside the configured Foundry host")

        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token()}",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        return self._open_json(urllib.request.Request(url, data=data, headers=headers, method=method))

    def status(self) -> dict[str, Any]:
        return {
            "configured": True,
            "host": self.host,
            "auth": "static-token" if self.static_token else "oauth-client-credentials",
            "scopes": self.scopes.split(),
            "writes_enabled": self.writes_enabled,
        }

    def list_ontologies(self, page_size: int = 100, page_token: Optional[str] = None) -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/v2/ontologies",
            query={"pageSize": max(1, min(page_size, 1000)), "pageToken": page_token},
        )

    def list_object_types(
        self,
        ontology: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> dict[str, Any]:
        ontology = urllib.parse.quote(ontology, safe="")
        return self.request(
            "GET",
            f"/api/v2/ontologies/{ontology}/objectTypes",
            query={"pageSize": max(1, min(page_size, 1000)), "pageToken": page_token},
        )

    def list_objects(
        self,
        ontology: str,
        object_type: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
        select: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        ontology = urllib.parse.quote(ontology, safe="")
        object_type = urllib.parse.quote(object_type, safe="")
        return self.request(
            "GET",
            f"/api/v2/ontologies/{ontology}/objects/{object_type}",
            query={
                "pageSize": max(1, min(page_size, 1000)),
                "pageToken": page_token,
                "select": select,
            },
        )

    def get_object(
        self,
        ontology: str,
        object_type: str,
        primary_key: str,
        select: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        ontology = urllib.parse.quote(ontology, safe="")
        object_type = urllib.parse.quote(object_type, safe="")
        primary_key = urllib.parse.quote(primary_key, safe="")
        return self.request(
            "GET",
            f"/api/v2/ontologies/{ontology}/objects/{object_type}/{primary_key}",
            query={"select": select},
        )

    def search_objects(
        self,
        ontology: str,
        object_type: str,
        search_body: dict[str, Any],
    ) -> dict[str, Any]:
        ontology = urllib.parse.quote(ontology, safe="")
        object_type = urllib.parse.quote(object_type, safe="")
        return self.request(
            "POST",
            f"/api/v2/ontologies/{ontology}/objects/{object_type}/search",
            body=search_body,
        )

    def apply_action(
        self,
        ontology: str,
        action: str,
        parameters: dict[str, Any],
        *,
        options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        ontology = urllib.parse.quote(ontology, safe="")
        action = urllib.parse.quote(action, safe="")
        payload: dict[str, Any] = {"parameters": parameters}
        if options:
            payload["options"] = options
        return self.request(
            "POST",
            f"/api/v2/ontologies/{ontology}/actions/{action}/apply",
            body=payload,
            write=True,
        )
