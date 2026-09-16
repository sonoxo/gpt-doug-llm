"""Palantir MCP tool profile for the authorized Zyra Foundry enrollment.

This module does not authenticate or bypass Foundry controls. It provides a
host-pinned configuration contract for two supported Palantir tool planes:

- Palantir MCP: development/build tools for datasets, transforms, repositories,
  Ontology schema, actions, and other platform resources.
- Ontology MCP: application-scoped runtime tools for exposed object types,
  actions, query functions, and AIP Logic/agent functions.

Credentials are always supplied out-of-band through environment variables or
the MCP client's secure credential store. No token or client secret belongs in
this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Any

ZYRA_FOUNDRY_HOST = "zyra.usw-17.palantirfoundry.com"
ZYRA_FOUNDRY_URL = f"https://{ZYRA_FOUNDRY_HOST}"


class PalantirMcpConfigurationError(RuntimeError):
    """Raised when the configured Foundry/MCP profile is unsafe or incomplete."""


@dataclass(frozen=True)
class ToolPlane:
    name: str
    purpose: str
    authority: str
    mutates_schema: bool
    mutates_ontology_data: bool
    credential_mode: str


BUILDER_PLANE = ToolPlane(
    name="palantir-mcp",
    purpose="Build and modify Foundry development resources under Palantir permissions.",
    authority="Foundry user/scoped token permissions plus Palantir MCP enablement.",
    mutates_schema=True,
    mutates_ontology_data=False,
    credential_mode="FOUNDRY_TOKEN or in-platform scoped token",
)

RUNTIME_PLANE = ToolPlane(
    name="ontology-mcp",
    purpose="Expose selected Ontology objects, actions, queries, and AIP functions as tools.",
    authority="Developer Console application restrictions plus OAuth/user/service permissions.",
    mutates_schema=False,
    mutates_ontology_data=True,
    credential_mode="OAuth authorization-code or client-credentials grant",
)


def _normalize_foundry_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        return ""
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise PalantirMcpConfigurationError("Foundry URL must be HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PalantirMcpConfigurationError("Foundry URL must not contain credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise PalantirMcpConfigurationError(
            "Use the Foundry enrollment origin only; do not configure a /workspace/... UI path"
        )
    if parsed.hostname.lower() != ZYRA_FOUNDRY_HOST:
        raise PalantirMcpConfigurationError(
            f"Foundry host must remain pinned to {ZYRA_FOUNDRY_HOST}"
        )
    return ZYRA_FOUNDRY_URL


def palantir_mcp_stdio_config() -> dict[str, Any]:
    """Return a secret-free stdio MCP configuration for supported desktop/IDE clients."""
    return {
        "mcpServers": {
            "palantir-mcp": {
                "type": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "palantir-mcp",
                    "--foundry-api-url",
                    ZYRA_FOUNDRY_URL,
                ],
                "env": {
                    "FOUNDRY_TOKEN": "${FOUNDRY_TOKEN}",
                },
            }
        }
    }


def status() -> dict[str, Any]:
    configured_url = os.getenv("FOUNDRY_BASE_URL", ZYRA_FOUNDRY_URL).strip()
    normalized_url = _normalize_foundry_origin(configured_url)
    configured_host = os.getenv("FOUNDRY_ALLOWED_HOST", ZYRA_FOUNDRY_HOST).strip().lower()
    if configured_host != ZYRA_FOUNDRY_HOST:
        raise PalantirMcpConfigurationError(
            f"FOUNDRY_ALLOWED_HOST must remain {ZYRA_FOUNDRY_HOST}"
        )

    token_present = bool(os.getenv("FOUNDRY_TOKEN", "").strip())
    oauth_present = bool(
        os.getenv("FOUNDRY_CLIENT_ID", "").strip()
        and os.getenv("FOUNDRY_CLIENT_SECRET", "").strip()
    )
    omcp_url_present = bool(os.getenv("FOUNDRY_ONTOLOGY_MCP_URL", "").strip())

    return {
        "profile": "ZYRA_PALANTIR_MCP",
        "foundry_origin": normalized_url,
        "allowed_host": configured_host,
        "builder_plane": asdict(BUILDER_PLANE),
        "runtime_plane": asdict(RUNTIME_PLANE),
        "local_readiness": {
            "palantir_mcp_token_present": token_present,
            "foundry_rest_oauth_present": oauth_present,
            "ontology_mcp_url_present": omcp_url_present,
            "palantir_mcp_control_panel_enablement": "VERIFY_IN_FOUNDRY",
            "ontology_mcp_developer_console_enablement": "VERIFY_IN_FOUNDRY",
        },
        "secrets_committed": False,
        "backdoor_channel": False,
        "supported_channels": ["PALANTIR_MCP_BUILDER", "ONTOLOGY_MCP_RUNTIME", "FOUNDRY_REST_AIP"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Zyra Foundry MCP profile")
    parser.add_argument("command", choices=("status", "config"), nargs="?", default="status")
    args = parser.parse_args()
    try:
        payload = status() if args.command == "status" else palantir_mcp_stdio_config()
    except PalantirMcpConfigurationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
