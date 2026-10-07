# GPT-DOUG Integrated Platform Spine

This document defines the canonical integration path for Eagle Eye, ZYRA Intelligence
Cloud, the Data Spider, security fusion, robotics simulations, astronomical context,
and the other GPT-DOUG visual modules.

## Runtime topology

```text
EAGLE EYE / SECURITY FUSION / LAB UIs
                 |
          core-client.js
                 |
      GPT-DOUG CORE PLATFORM
                 |
     +-----------+-----------+
     |           |           |
  Event API   Ontology    Case/Intel
     |           |           |
  WebSocket   Sources      Reports
     |           |           |
     +------- Audit Chain ---+
                 |
       SQLAlchemy data plane
                 |
       SQLite local / Postgres production
```

## Canonical platform API

Public read-only:

- `GET /healthz`
- `GET /api/v1/platform/manifest`
- `GET /api/v1/ontology/schema`
- `GET /api/v1/sources`
- `GET /api/v1/public/events`
- `WS /ws/v1/events`

Authenticated workspace APIs:

- `GET /api/v1/status`
- `GET/POST /api/v1/events`
- `GET/POST /api/v1/cases`
- `GET/POST /api/v1/intel`
- `GET/POST /api/v1/reports`
- `GET/POST /api/v1/alerts`
- `GET /api/v1/audit`
- `GET /api/v1/audit/verify`

The browser event stream only exposes events classified PUBLIC, TRAINING, or
SIMULATION. The API blocks operational weapon-control, target-selection,
strike-planning, payload-release, lethal-engagement, and real-person hostile
classification event types.

## Durable vs realtime responsibilities

Postgres/SQLite is the source of truth. WebSocket delivery is only the low-latency
fan-out plane. Clients recover from disconnects by reading the durable event
history endpoint.

## Browser integration

`eagleeye-cloud/core-client.js` provides:

```js
GPT_CORE.status()
GPT_CORE.bootstrap()
GPT_CORE.reconnect()
GPT_CORE.setBase("https://example-core")
GPT_CORE.clearBase()
```

The Security Fusion page consumes the shared event stream and turns public or
synthetic platform events into visible nodes on the existing layers rather than
creating another visualization layer.

## Local launch

```sh
cd ~/gpt-doug-llm
git fetch origin
git switch cloud/eagleeye-free
git pull --ff-only
chmod +x scripts/install-gpt-doug-platform
./scripts/install-gpt-doug-platform
source ~/.zshrc
gpt-doug-platform
```

Verification:

```sh
gpt-doug-platform-doctor
```

Local URLs:

- UI: `http://127.0.0.1:8080/quantum-security-fusion.html`
- Core API: `http://127.0.0.1:8090`
- OpenAPI: `http://127.0.0.1:8090/docs`
- WebSocket: `ws://127.0.0.1:8090/ws/v1/events`

Local development uses demo role tokens. They are deliberately disabled in the
production configuration.

## Render infrastructure

`render.platform.yaml` defines the canonical future stack:

- GPT-DOUG Core web service
- PostgreSQL state database
- GPT-DOUG static UI
- generated production secrets
- strict browser origin configuration

The existing public Eagle Eye site remains a public demonstration environment.

## Production gap

The current cloud Core service can operate as a public read-only integration
surface using local service storage, but durable production event/case history
requires a dedicated managed Postgres instance. Do not reuse an unrelated
database simply to satisfy this dependency.

A green deployment is software availability, not CMMC, FedRAMP, FIPS, RMF/ATO,
CUI, NSS, or classified-system authorization.
