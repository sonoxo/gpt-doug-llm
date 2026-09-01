# XUNI Connector Fabric

GPT-Doug-LLM is the connector/control layer for XUNI gaming cloud.

## Contract
Every connector exposes:
- stable connector id
- category
- capability list
- health state
- required external configuration
- authoritative documentation source
- explicit licensed-runtime boundary when applicable

Health states:
- `READY`
- `CONFIG_REQUIRED`
- `LICENSED_RUNTIME_REQUIRED`
- `DISABLED`

## Free local baseline
The following require no paid hosted service and are expected to be READY in CI/local development:
- `xuni-local-cloud`: identity, profiles, presence, parties, lobbies, matchmaking, sessions, cloud saves, achievements, entitlements, leaderboards, telemetry, moderation events, build metadata
- `sqlite`: durable local data
- `websocket-sse`: realtime events
- `opentelemetry`: traces, metrics and logs

This means every game feature can be developed and tested end-to-end before a provider account is attached.

## Xbox / Microsoft production adapters
- `xbox-gdk`: Gaming Runtime, GameInput, XTaskQueue/XAsync, D3D12 and console packaging lifecycle
- `xbox-user`: XUser sign-in and user events
- `xbox-services`: Xbox profile/presence/social/achievements/leaderboards/multiplayer
- `xstore`: Store catalog, licenses, entitlements and purchase UI
- `playfab`: player data, cloud saves, economy, statistics/leaderboards, multiplayer servers, matchmaking, lobbies and telemetry

The public repository never contains Microsoft GDK binaries/private headers, NDA-only documentation, sandbox credentials, certificates, signing material or service secrets. Native Xbox connectors report `LICENSED_RUNTIME_REQUIRED` until executed inside the authorized GDK environment.

## DevOps adapters
- GitHub: source, issues, pull requests, Actions, releases, artifacts
- Replit: rapid prototype/preview/deployment integration
- Vercel: web/control-plane preview/deployment integration

Provider connectors use environment configuration only. They never embed credentials in source control.

## Capability resolution
Consumers should request capabilities rather than hard-code providers. Example: `cloud_saves` can resolve to the free `xuni-local-cloud` adapter during development and to PlayFab/connected-storage adapters in production.

## Operating rule
`XUNI game -> GPT-Doug capability request -> connector registry -> ready provider -> health/evidence -> game service`

If no production provider is configured, the local baseline remains functional instead of breaking development.
