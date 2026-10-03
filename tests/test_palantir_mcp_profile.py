from __future__ import annotations

import json

import pytest

from palantir_mcp_profile import (
    PalantirMcpConfigurationError,
    ZYRA_FOUNDRY_HOST,
    ZYRA_FOUNDRY_URL,
    palantir_mcp_stdio_config,
    status,
)


def test_stdio_config_is_host_pinned_and_secret_free():
    config = palantir_mcp_stdio_config()
    server = config["mcpServers"]["palantir-mcp"]
    assert server["command"] == "npx"
    assert server["args"][-1] == ZYRA_FOUNDRY_URL
    assert server["env"]["FOUNDRY_TOKEN"] == "${FOUNDRY_TOKEN}"
    serialized = json.dumps(config)
    assert "client_secret" not in serialized.lower()


def test_status_defaults_to_zyra_origin(monkeypatch):
    for key in (
        "FOUNDRY_BASE_URL",
        "FOUNDRY_ALLOWED_HOST",
        "FOUNDRY_TOKEN",
        "FOUNDRY_CLIENT_ID",
        "FOUNDRY_CLIENT_SECRET",
        "FOUNDRY_ONTOLOGY_MCP_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    value = status()
    assert value["foundry_origin"] == ZYRA_FOUNDRY_URL
    assert value["allowed_host"] == ZYRA_FOUNDRY_HOST
    assert value["backdoor_channel"] is False
    assert value["secrets_committed"] is False


def test_workspace_ui_url_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "FOUNDRY_BASE_URL",
        f"{ZYRA_FOUNDRY_URL}/workspace/now/platform",
    )
    with pytest.raises(PalantirMcpConfigurationError):
        status()


def test_other_host_is_rejected(monkeypatch):
    monkeypatch.setenv("FOUNDRY_BASE_URL", "https://example.palantirfoundry.com")
    with pytest.raises(PalantirMcpConfigurationError):
        status()
