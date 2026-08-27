# ZYRA Intelligence Cloud

**Private business-intelligence and cyber-defense platform. Not a government agency.**

ZYRA Intelligence Cloud turns the existing GPT-DOUG / ZYRA / GPT-GLASSONION intelligence stack into a deployable multi-tenant business platform for client workspaces, analyst operations, provenance-aware intelligence, reports, alerts, locked-ontology queries, live-source deltas, and tamper-evident audit evidence.

## Command architecture

```text
CLIENTS / ANALYSTS / DIRECTOR / AUDITOR
                 │
                 ▼
        ZYRA INTELLIGENCE CLOUD
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
  CASE OPS    INTEL OPS    CLIENT PRODUCT
     │           │            │
     │           ├─ provenance digest
     │           ├─ confidence/class
     │           └─ case relationships
     │
     ├──────────────┬───────────────┐
     ▼              ▼               ▼
MASTER-LOCK     GLASSONION       LIVE INTEL
ONTOLOGY        OVERLAY          CHANGES
     │              │               │
     └──────────────┴───────────────┘
                    │
                    ▼
          HMAC-CHAINED AUDIT
```

## Business capabilities

- Multi-tenant intelligence workspaces
- Director, analyst, auditor, and client roles
- Intelligence cases with priority and tags
- Provenance-required intelligence intake
- Source SHA-256 evidence digesting
- Intelligence classes and confidence levels
- Case-to-intelligence relationship graph
- Client-ready reports
- Operational alerts
- Read-only MASTER-LOCK ontology queries
- Read-only GPT-GLASSONION queries
- Live public defensive-intelligence delta surface
- HMAC-chained tamper-evident audit events
- SQLite development mode
- PostgreSQL production mode
- Container deployment with `/healthz`
- OpenAPI at `/docs`

## Legal/identity boundary

The platform must remain visibly identified as a **private commercial intelligence company**. Do not use the application, branding, domains, credentials, documents, or UI to impersonate the CIA, FBI, DoD, Commonwealth of Virginia, or any other government entity. Government-source intelligence can be ingested with provenance while preserving its actual evidentiary status.

## Local launch

```bash
cd ~/gpt-doug-llm
python3 -m venv .venv-agency
source .venv-agency/bin/activate
pip install -r agency_cloud/requirements.txt
cp agency_cloud/.env.example agency_cloud/.env
```

Export development configuration:

```bash
export AGENCY_ALLOW_DEMO_AUTH=true
export AGENCY_ENVIRONMENT=development
uvicorn agency_cloud.app:app --host 127.0.0.1 --port 8080 --reload
```

Open `http://127.0.0.1:8080`.

Development-only tokens when `AGENCY_ALLOW_DEMO_AUTH=true`:

```text
director-demo
analyst-demo
auditor-demo
client-demo
```

Never enable demo authentication in production.

## Production secrets

Generate unique secrets and inject them through your cloud secret manager:

```text
AGENCY_ENVIRONMENT=production
AGENCY_DATABASE_URL=postgresql+psycopg://...
AGENCY_AUDIT_KEY=<strong random value>
AGENCY_DIRECTOR_TOKEN=<strong random value>
AGENCY_ANALYST_TOKEN=<strong random value>
AGENCY_AUDITOR_TOKEN=<strong random value>
AGENCY_CLIENT_TOKEN=<strong random value>
AGENCY_ALLOW_DEMO_AUTH=false
```

The service refuses production startup if the required role tokens or audit key are absent or if demo authentication is enabled.

## PostgreSQL stack

From the repository root:

```bash
export POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export AGENCY_AUDIT_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AGENCY_DIRECTOR_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AGENCY_ANALYST_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AGENCY_AUDITOR_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AGENCY_CLIENT_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose -f agency_cloud/docker-compose.yml up --build
```

## API command surface

```text
GET  /healthz
GET  /api/v1/meta
GET  /api/v1/workspaces
POST /api/v1/workspaces
GET  /api/v1/status
GET  /api/v1/cases
POST /api/v1/cases
GET  /api/v1/intel
POST /api/v1/intel
POST /api/v1/cases/{case_id}/intel/{intel_id}
GET  /api/v1/reports
POST /api/v1/reports
GET  /api/v1/alerts
POST /api/v1/alerts
GET  /api/v1/audit
GET  /api/v1/audit/verify
GET  /api/v1/live/changes
GET  /api/v1/ontology/status
POST /api/v1/ontology/query
GET  /api/v1/glassonion/status
POST /api/v1/glassonion/query
```

Authenticated tenant requests use:

```text
Authorization: Bearer <role-token>
X-Zyra-Workspace: ws_...
```

## Production deployment target

The application is container-native. Use the same image on a managed container platform with:

1. TLS termination at the platform/load balancer.
2. Managed PostgreSQL with encrypted storage and backups.
3. Cloud secret manager for every role token and `AGENCY_AUDIT_KEY`.
4. Private network access between the application and database.
5. Central logs/metrics and alerting.
6. Image vulnerability scanning and signed releases.
7. External identity provider/OIDC before broad enterprise use.
8. Independent security assessment before handling regulated or government-controlled data.

The repository CI builds and tests the cloud application. A green software build means the application code passed its automated gate; it is not a government authorization or accreditation.
