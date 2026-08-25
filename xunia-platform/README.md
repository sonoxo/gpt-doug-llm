# XUNIA Platform v1

XUNIA Platform is an original full-stack ontology + AIP control plane built for XUNIA Chain and SONOXO integrations. It provides an object/relation ontology, bounded agentic workflows, approval-gated tools, persistent execution state, a hash-chained audit trail, REST APIs, and a browser operations console.

This is a clean-room XUNIA implementation. It does not contain proprietary Palantir source code, private APIs, branding, or copied UI assets.

## Production capabilities

- persistent ontology objects and links with atomic state writes
- optional AES-256-GCM encryption of persisted ontology/AIP state
- object search, type inventory, neighbor traversal, upsert, and controlled delete/cascade
- AIP agent registry and ontology grounding
- bounded tool registry with `low`, `medium`, and `high` risk levels
- approval gates for side-effecting tools
- persisted AIP runs and pending approvals across restarts
- SHA-256 hash-chained audit records with integrity verification
- API-key authentication and RBAC (`viewer`, `editor`, `operator`, `admin`)
- constant-time API-key comparison
- sovereign realm and region enforcement
- outbound AIP/network egress allowlisting with air-gap mode
- customer-key boundary metadata and state-encryption readiness gates
- request body limits, per-client rate limits, security headers, optional CORS allow-origin
- liveness, readiness, and Prometheus-format metrics
- graceful shutdown and HTTP timeout hardening
- XUNIA Chain health tool and SONOXO telemetry tool
- optional external model gateway with timeout and bearer-token support
- browser console with session-scoped API-key connection
- hardened non-root Docker image
- Docker Compose and Kubernetes deployment manifests
- CI build, tests, RBAC/persistence restart tests, sovereign encrypted-state test, and container build

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

## Sovereign mode

Sovereign mode creates a deployment-level data and execution boundary. It is designed for private cloud, on-premises, restricted-network, and air-gapped deployments.

```bash
export XUNIA_SOVEREIGNTY_ENFORCED=1
export XUNIA_REALM_ID=xunia-us-va
export XUNIA_REGION=us-va
export XUNIA_ALLOWED_REGIONS=us-va
export XUNIA_KEY_AUTHORITY=customer
export XUNIA_CUSTOMER_KEY_ID='kms://customer/xunia-platform'
export XUNIA_REQUIRE_ENCRYPTED_STATE=1
export XUNIA_STATE_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

Sovereign controls:

- every credential is scoped to the deployment realm; API-key entries may explicitly set `realm`
- optional `X-Xunia-Realm` and `X-Xunia-Region` request headers are fail-closed when they cross the configured boundary
- AIP model calls, SONOXO telemetry, and XUNIA Chain network tools pass through the egress policy before any network request occurs
- loopback, RFC1918/link-local, single-label internal service names, and `.internal`/`.local` hosts are treated as private-network targets
- public origins are denied unless their exact origin appears in `XUNIA_EGRESS_ALLOWLIST`
- `XUNIA_AIR_GAPPED=1` denies public egress regardless of the allowlist
- `XUNIA_REQUIRE_ENCRYPTED_STATE=1` makes readiness fail when the state-encryption key is absent
- state encryption uses AES-256-GCM with a 32-byte base64 key supplied at runtime; the key is never written into state files
- `XUNIA_KEY_AUTHORITY=customer` requires a customer key identifier in readiness, allowing the runtime secret to be sourced from the customer KMS/HSM or secret manager
- the canonical sovereignty manifest has a SHA-256 fingerprint; set `XUNIA_SOVEREIGNTY_EXPECTED_SHA256` to lock a deployment to an approved policy configuration

The Kubernetes manifest adds a default-deny egress policy that only permits XUNIA Chain, SONOXO, and cluster DNS by default. Add explicit NetworkPolicy destinations when an external model gateway or data service is approved.

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

In sovereign deployments, callers or trusted ingress proxies may additionally send:

```http
X-Xunia-Realm: xunia-us-va
X-Xunia-Region: us-va
```

## AIP execution pipeline

```text
request
  -> authentication / RBAC
  -> sovereign realm + region gate
  -> ontology context
  -> model gateway
  -> outbound sovereignty gate
  -> bounded plan
  -> tool allowlist
  -> risk policy
  -> automatic low-risk reads OR approval-required side effects
  -> execution
  -> encrypted persistent run state
  -> hash-chained audit record
```

The default analyst and operator require approval for `medium` and `high` risk tools. SONOXO telemetry writes are `medium`; ontology reads and XUNIA Chain health checks are `low`.

## Persistence

Set `XUNIA_DATA_DIR` to enable file persistence. Two atomic state files are maintained:

```text
ontology.json
aip.json
```

Set `XUNIA_STATE_ENCRYPTION_KEY` to a base64-encoded 32-byte key to store both files as AES-256-GCM envelopes. Existing plaintext files remain readable for migration, but new writes are encrypted whenever the key is configured. If an encrypted file cannot be decrypted, persistence fails closed and writes are blocked to avoid overwriting protected state.

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

The endpoint may return `text`, `response`, or `output`. If no model URL is configured, AIP uses a deterministic local fallback for development. In sovereign mode, external model origins must be explicitly allowed by both the application egress allowlist and the deployment network policy.

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
- sovereign mode can pin data processing to one or more declared regions and deny cross-realm requests
- public outbound model/telemetry connections are fail-closed unless approved

This API-key baseline is suitable for controlled/private deployment. For large multi-user deployments, place the platform behind your organization’s identity-aware proxy/SSO and map authenticated identities into the XUNIA role model.

## Deployment

See `deploy/DEPLOYMENT.md` for Docker Compose and Kubernetes procedures. `.env.example` documents all runtime variables.
