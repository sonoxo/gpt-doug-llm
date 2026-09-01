"""XUNI gaming-cloud connector fabric.

This module provides one normalized capability/health contract for local-first and
provider-backed gaming services. It never embeds credentials. Provider adapters become
READY only when their required environment configuration is present; local/mock
connectors remain usable for free CI and development.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Iterable


class ConnectorState(str, Enum):
    READY = "READY"
    CONFIG_REQUIRED = "CONFIG_REQUIRED"
    LICENSED_RUNTIME_REQUIRED = "LICENSED_RUNTIME_REQUIRED"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class ConnectorSpec:
    id: str
    name: str
    category: str
    capabilities: tuple[str, ...]
    required_env: tuple[str, ...] = ()
    licensed_runtime: bool = False
    local_first: bool = False
    authoritative_source: str | None = None


@dataclass(frozen=True)
class ConnectorHealth:
    id: str
    state: ConnectorState
    capabilities: tuple[str, ...]
    missing_env: tuple[str, ...] = ()
    detail: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["state"] = self.state.value
        return data


CONNECTORS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        "xuni-local-cloud", "XUNI Local Cloud", "core",
        ("identity", "profiles", "presence", "parties", "lobbies", "matchmaking", "sessions", "cloud_saves", "achievements", "entitlements", "leaderboards", "telemetry", "moderation_events", "build_metadata"),
        local_first=True,
    ),
    ConnectorSpec(
        "xbox-gdk", "Microsoft GDK Native Runtime", "platform",
        ("gaming_runtime", "gameinput", "xtaskqueue", "xasync", "d3d12", "suspend_resume", "xvc_packaging"),
        licensed_runtime=True,
        authoritative_source="https://learn.microsoft.com/en-us/gaming/gdk/",
    ),
    ConnectorSpec(
        "xbox-user", "Xbox XUser Identity", "identity",
        ("sign_in", "user_change_events", "gamertag_identity"),
        licensed_runtime=True,
        authoritative_source="https://learn.microsoft.com/en-us/gaming/gdk/docs/features/common/user/users-and-accounts/",
    ),
    ConnectorSpec(
        "xbox-services", "Xbox Services / XSAPI", "social",
        ("profile", "presence", "social", "achievements", "leaderboards", "multiplayer"),
        licensed_runtime=True,
        authoritative_source="https://learn.microsoft.com/en-us/gaming/gdk/docs/services/",
    ),
    ConnectorSpec(
        "xstore", "Microsoft Store / XStore", "commerce",
        ("catalog", "entitlements", "license", "purchase_ui", "consumables"),
        licensed_runtime=True,
        authoritative_source="https://learn.microsoft.com/en-us/gaming/gdk/docs/store/",
    ),
    ConnectorSpec(
        "playfab", "Microsoft PlayFab", "cloud",
        ("identity", "player_data", "cloud_saves", "economy", "statistics", "leaderboards", "multiplayer_servers", "matchmaking", "lobbies", "telemetry"),
        required_env=("XUNI_PLAYFAB_TITLE_ID",),
        authoritative_source="https://learn.microsoft.com/en-us/gaming/playfab/",
    ),
    ConnectorSpec(
        "github", "GitHub", "devops",
        ("source", "issues", "pull_requests", "actions", "releases", "artifacts"),
        required_env=("GITHUB_TOKEN",),
        authoritative_source="https://docs.github.com/",
    ),
    ConnectorSpec(
        "replit", "Replit", "devops",
        ("prototype_build", "preview", "deployment"),
        required_env=("XUNI_REPLIT_TOKEN",),
        authoritative_source="https://docs.replit.com/",
    ),
    ConnectorSpec(
        "vercel", "Vercel", "devops",
        ("web_build", "preview", "deployment", "edge_api"),
        required_env=("VERCEL_TOKEN",),
        authoritative_source="https://vercel.com/docs",
    ),
    ConnectorSpec(
        "opentelemetry", "OpenTelemetry", "observability",
        ("traces", "metrics", "logs"),
        local_first=True,
        authoritative_source="https://opentelemetry.io/docs/",
    ),
    ConnectorSpec(
        "sqlite", "SQLite", "storage",
        ("profiles", "sessions", "saves", "leaderboards", "telemetry_buffer"),
        local_first=True,
        authoritative_source="https://sqlite.org/docs.html",
    ),
    ConnectorSpec(
        "websocket-sse", "WebSocket / SSE", "realtime",
        ("presence_stream", "party_events", "match_events", "telemetry_stream"),
        local_first=True,
    ),
)


class ConnectorRegistry:
    def __init__(self, specs: Iterable[ConnectorSpec] = CONNECTORS, env: dict[str, str] | None = None):
        self.specs = {spec.id: spec for spec in specs}
        self.env = dict(os.environ if env is None else env)

    def get(self, connector_id: str) -> ConnectorSpec:
        try:
            return self.specs[connector_id]
        except KeyError as exc:
            raise KeyError(f"UNKNOWN_CONNECTOR:{connector_id}") from exc

    def health(self, connector_id: str, *, licensed_runtime_available: bool = False) -> ConnectorHealth:
        spec = self.get(connector_id)
        missing = tuple(key for key in spec.required_env if not self.env.get(key))
        if spec.licensed_runtime and not licensed_runtime_available:
            return ConnectorHealth(spec.id, ConnectorState.LICENSED_RUNTIME_REQUIRED, spec.capabilities, missing, "Install/use the authorized Microsoft GDK environment; public CI uses mocks.")
        if missing:
            return ConnectorHealth(spec.id, ConnectorState.CONFIG_REQUIRED, spec.capabilities, missing, "Credentials/configuration are external to source control.")
        return ConnectorHealth(spec.id, ConnectorState.READY, spec.capabilities, (), "Local/mock connector ready." if spec.local_first else "Provider connector configured.")

    def report(self, *, licensed_runtime_available: bool = False) -> list[dict]:
        return [self.health(cid, licensed_runtime_available=licensed_runtime_available).to_dict() for cid in sorted(self.specs)]

    def resolve_capability(self, capability: str, *, licensed_runtime_available: bool = False) -> list[ConnectorHealth]:
        matches = []
        for spec in self.specs.values():
            if capability in spec.capabilities:
                matches.append(self.health(spec.id, licensed_runtime_available=licensed_runtime_available))
        return sorted(matches, key=lambda h: (h.state != ConnectorState.READY, h.id))

    def assert_free_local_baseline(self) -> None:
        required = {"xuni-local-cloud", "opentelemetry", "sqlite", "websocket-sse"}
        for cid in required:
            health = self.health(cid)
            if health.state is not ConnectorState.READY:
                raise RuntimeError(f"LOCAL_BASELINE_NOT_READY:{cid}:{health.state.value}")


def connector_report(env: dict[str, str] | None = None, *, licensed_runtime_available: bool = False) -> list[dict]:
    return ConnectorRegistry(env=env).report(licensed_runtime_available=licensed_runtime_available)
