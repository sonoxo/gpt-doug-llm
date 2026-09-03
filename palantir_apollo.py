"""Palantir Apollo deployment adapter.

Apollo exposes Hub data through GraphQL and supports CI publishing through
apollo-cli. This module implements both control surfaces without shell=True and
requires explicit approval for publishing a Product Release.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Optional
import urllib.parse
import urllib.request
import ssl


class ApolloError(RuntimeError):
    pass


@dataclass
class ApolloClient:
    apollo_url: str
    token: str = ""
    client_id: str = ""
    client_secret: str = ""
    graphql_url: str = ""
    cli_path: str = "apollo-cli"
    timeout: float = 20.0

    @classmethod
    def from_environment(cls) -> Optional["ApolloClient"]:
        apollo_url = os.getenv("APOLLO_URL", "").strip()
        if not apollo_url:
            return None
        return cls(
            apollo_url=apollo_url.rstrip("/"),
            token=os.getenv("APOLLO_TOKEN", "").strip(),
            client_id=os.getenv("APOLLO_CLIENT_ID", "").strip(),
            client_secret=os.getenv("APOLLO_CLIENT_SECRET", "").strip(),
            graphql_url=os.getenv("APOLLO_GRAPHQL_URL", "").strip(),
            cli_path=os.getenv("APOLLO_CLI", "apollo-cli").strip() or "apollo-cli",
            timeout=float(os.getenv("APOLLO_TIMEOUT_SECONDS", "20")),
        )

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlparse(self.apollo_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ApolloError("APOLLO_URL must be HTTPS")
        if not self.token and not (self.client_id and self.client_secret):
            raise ApolloError("Configure APOLLO_TOKEN or Apollo service-account credentials")
        if self.graphql_url:
            gql = urllib.parse.urlparse(self.graphql_url)
            if gql.scheme != "https" or gql.hostname != parsed.hostname:
                raise ApolloError("APOLLO_GRAPHQL_URL must use the same HTTPS Apollo host")

    def status(self) -> dict[str, Any]:
        return {
            "configured": True,
            "host": urllib.parse.urlparse(self.apollo_url).hostname,
            "auth": "token" if self.token else "service-account",
            "graphql_configured": bool(self.graphql_url),
            "cli_available": shutil.which(self.cli_path) is not None,
        }

    def graphql(self, query: str, variables: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not self.graphql_url:
            raise ApolloError("APOLLO_GRAPHQL_URL is not configured")
        if not self.token:
            raise ApolloError("GraphQL calls currently require APOLLO_TOKEN")
        request = urllib.request.Request(
            self.graphql_url,
            data=json.dumps({"query": query, "variables": variables or {}}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=self.timeout,
            context=ssl.create_default_context(),
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ApolloError("Apollo GraphQL response was not an object")
        if payload.get("errors"):
            raise ApolloError(f"Apollo GraphQL returned errors: {payload['errors']}")
        return payload

    def get_current_user(self) -> dict[str, Any]:
        return self.graphql("query GetCurrentUser { me { id fullName } }")

    def get_environments(self, page_size: int = 100) -> dict[str, Any]:
        page_size = max(1, min(page_size, 1000))
        return self.graphql(
            "query GetEnvironments($pageSize: Int!) { apollo { environments(pageSize: $pageSize) { environments { id } } } }",
            {"pageSize": page_size},
        )

    def _auth_args(self) -> list[str]:
        if self.token:
            return ["--apollo-token", self.token]
        return [
            "--apollo-client-id",
            self.client_id,
            "--apollo-client-secret",
            self.client_secret,
        ]

    def publish_product_release(
        self,
        *,
        manifest: str | Path,
        approve: bool = False,
        default_config: str | Path | None = None,
        config_schema: str | Path | None = None,
        space_id: str = "",
    ) -> dict[str, Any]:
        """Publish an Apollo Product Release using the documented CLI flow."""
        if not approve:
            raise ApolloError("Apollo publish requires approve=True")
        executable = shutil.which(self.cli_path)
        if not executable:
            raise ApolloError("apollo-cli is not installed or APOLLO_CLI is incorrect")
        manifest_path = Path(manifest).resolve()
        if not manifest_path.is_file():
            raise ApolloError(f"Apollo manifest not found: {manifest_path}")
        cmd = [
            executable,
            "product-release",
            "create",
            "--apollo-url",
            self.apollo_url,
            *self._auth_args(),
            "--manifest",
            str(manifest_path),
        ]
        if default_config:
            cmd.extend(["--default-config", str(Path(default_config).resolve())])
        if config_schema:
            cmd.extend(["--config-schema", str(Path(config_schema).resolve())])
        if space_id:
            cmd.extend(["--space-id", space_id])
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise ApolloError(f"apollo-cli failed: {completed.stderr[-2000:]}")
        return {"published": True, "stdout": completed.stdout[-4000:]}


def validate_apollo_manifest(payload: dict[str, Any]) -> list[str]:
    """Validate mandatory Apollo Product Release manifest fields."""
    required = ["product-type", "product-group", "product-name", "product-version"]
    return [name for name in required if not str(payload.get(name, "")).strip()]
