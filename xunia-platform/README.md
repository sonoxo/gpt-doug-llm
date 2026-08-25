# XUNIA Platform v1

XUNIA Platform is an original full-stack ontology + AIP control plane built for XUNIA Chain and SONOXO integrations. It provides an object/relation ontology, bounded agentic workflows, approval-gated tools, persistent execution state, a hash-chained audit trail, REST APIs, and a browser operations console.

This is a clean-room XUNIA implementation. It does not contain proprietary Palantir source code, private APIs, branding, or copied UI assets.

## Production capabilities

- persistent ontology objects and links with atomic JSON state writes
- object search, type inventory, neighbor traversal, upsert, and controlled delete/cascade
- AIP agent registry and ontology grounding
- bounded tool registry with `low`, `medium`, and `high` risk levels
- approval gates for side-effecting tools
- persisted AIP runs and pending approvals across restarts
- SHA-256 hash-chained audit records with integrity verification
- API-key authentication and RBAC (`viewer`, `editor`, `operator`, `admin`)
- constant-time API-key comparison
- request body limits, per-client rate limits, security headers, optional CORS allow-origin
- liveness, readiness, and Prometheus-format metrics
- graceful shutdown and HTTP timeout hardening
- XUNIA Chain health tool and SONOXO telemetry tool
- optional external model gateway with timeout and bearer-token support
- browser console with session-scoped API-key connection
- hardened non-root Docker image
- Docker Compose and Kubernetes deployment manifests
- CI build, tests, authenticated smoke test, persistence restart test, and container build

## Roles

| Role | Access |
| --- | --- |
| `viewer` | read ontology, agents, tools, runs, status, metrics, audit |
| `editor` | viewer access + mutate ontology objects/links |
| `operator` | editor access + start AIP runs |
| `admin` | all access + approve gated tool execution and register agents |

When `XUNIA_AUTH_REQUIRED=0`, local development runs as an implicit admin. Production should always use `XUNIA_AUTH_REQUIRED=1`.

## Local build

```bash
cd xunia-platform
npm install
npm run test
npm start
```

Open `http://127.0.0.1:4400/`.

## Production start

```bash
export XUNIA_PLATFORM_HOST=0.0.0.0
export XUNIA_PLATFORM_PORT=4400
export XUNIA_DATA_DIR=/var/lib/xunia-platform
export XUNIA_AUTH_REQUIRED=1
export XUNIA_API_KEYS='{"replace-with-long-random-token":{"role":"admin","subject":"platform-admin"}}'
npm run build
npm start
```

Put TLS in front of the service before exposing it to an untrusted network.

## Core API

Public operational endpoints:

```text
GET /health
GET /ready
GET /api/session
```

Authenticated platform endpoints:

```text
GET    /api/platform/status
GET    /metrics
GET    /api/ontology
GET    /api/ontology/types
GET    /api/ontology/search?q=...&type=...
GET    /api/ontology/objects/:id
POST   /api/ontology/objects
DELETE /api/ontology/objects/:id?cascade=1
POST   /api/ontology/links
DELETE /api/ontology/links/:id
GET    /api/aip/agents
POST   /api/aip/agents
GET    /api/aip/tools
GET    /api/aip/runs
GET    /api/aip/runs/:id
POST   /api/aip/run
POST   /api/aip/runs/:runId/approve/:stepId
GET    /api/aip/audit
GET    /api/aip/audit/verify
```

Use either:

```http
Authorization: Bearer <api-key>
```

or:

```http
X-API-Key: <api-key>
```

## AIP execution pipeline

```text
request
  -> authentication / RBAC
  -> ontology context
  -> model gateway
  -> bounded plan
  -> tool allowlist
  -> risk policy
  -> automatic low-risk reads OR approval-required side effects
  -> execution
  -> persistent run state
  -> hash-chained audit record
```

The default analyst and operator require approval for `medium` and `high` risk tools. SONOXO telemetry writes are `medium`; ontology reads and XUNIA Chain health checks are `low`.

## Persistence

Set `XUNIA_DATA_DIR` to enable file persistence. Two atomic state files are maintained:

```text
ontology.json
aip.json
```

Without `XUNIA_DATA_DIR`, the platform runs in in-memory development mode. `/ready` reports the active persistence mode and any storage error.

## Model gateway

Set `XUNIA_MODEL_URL` and optionally `XUNIA_MODEL_TOKEN`. The platform sends:

```json
{
  "system": "...",
  "message": "...",
  "context": []
}
```

The endpoint may return `text`, `response`, or `output`. If no model URL is configured, AIP uses a deterministic local fallback for development.

## Security baseline

- no secrets are returned by status endpoints
- production auth fails readiness when auth is required but no API keys are configured
- API keys are compared with constant-time equality
- approval endpoints require `admin`
- side-effecting default AIP tools require approval
- CSP, frame denial, no-sniff, referrer, and permissions headers are applied
- request bodies and request rates are bounded
- reverse-proxy client IPs are trusted only when `XUNIA_TRUST_PROXY=1`
- container runs as an unprivileged user with a dedicated persistent volume

This API-key baseline is suitable for controlled/private deployment. For large multi-user deployments, place the platform behind your organization’s identity-aware proxy/SSO and map authenticated identities into the XUNIA role model.

## Deployment

See `deploy/DEPLOYMENT.md` for Docker Compose and Kubernetes procedures. `.env.example` documents all runtime variables.
