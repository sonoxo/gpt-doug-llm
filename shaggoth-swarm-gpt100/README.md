# Shaggoth Swarm GPT-100

A safe-by-default, local-first multi-agent orchestration framework for running up to 100 logical AI agents behind a single coordinator.

> **Naming note:** `GPT-100` is this project's 100-agent preset. It is not the name of an OpenAI model.

## What it does

- Creates a registry of 100 specialized logical agents by default.
- Decomposes a goal into bounded subtasks.
- Routes subtasks through a model adapter.
- Enforces explicit capability policy before any tool action.
- Aggregates results into a single swarm report.
- Provides a CLI and an optional HTTP API.
- Ships with deterministic tests and a zero-network mock adapter.
- Can continuously monitor explicitly authorized HTTP(S) endpoints.
- Uses normal production-service behavior: visible identity, standard authentication, bounded retries, rate limits, health checks, and structured audit events.
- Provides a scoped capability broker covering local development, APIs, GitHub, storage, queues, databases, schedules, email, calendar, telemetry, artifacts, models, and web search.

## Heartbeat and terminal install

If the shell says `zsh: command not found: shaggoth`, install the CLI into a
dedicated local virtual environment:

```bash
bash scripts/bootstrap-shaggoth.sh
```

The installer creates the virtual environment under
`~/.local/share/gpt-doug-shaggoth/venv`, symlinks `shaggoth` into
`~/.local/bin`, and adds that bin directory to `~/.zshrc` if necessary.

Verify the local runtime:

```bash
shaggoth heartbeat
shaggoth heartbeat --json
```

Continuously emit a heartbeat every five seconds:

```bash
shaggoth heartbeat --watch 5
```

Optionally include an explicit HTTP health endpoint in the pulse:

```bash
shaggoth heartbeat --endpoint http://127.0.0.1:8787/health
```

A normal local pulse reports the CLI process, 100-agent capacity, adapter,
active capability profile, and atomic-stack validity. It does not require the
API server to be running unless `--endpoint` is supplied.

## Atomic layers

Shaggoth now uses an eight-layer atomic execution model:

```text
L0 particle    immutable envelope, ID, trace, timestamp, digest
L1 atom        one scoped capability invocation
L2 molecule    bounded composition of atoms
L3 cell        one agent execution boundary
L4 swarm       bounded multi-agent coordination
L5 service     APIs, queues, storage, catalogs, connectors
L6 fabric      containers, Kubernetes, networking, scaling
L7 governance  policy, audit, provenance, risk, compliance
```

Execution moves upward one layer at a time. Any execution layer may emit a
governance record, but governance cannot silently re-enter the execution stack.

`AtomicEnvelope` preserves a trace ID across promotions and links each new
envelope to its parent. Capability broker atomic calls record only capability
metadata, not handler arguments or results.

```bash
shaggoth layers
shaggoth layers --validate
shaggoth layers --json
```

The API exposes the same manifest at `GET /layers`.

See `docs/ATOMIC_LAYERS.md` for the complete contracts and invariants.

## Capability profiles

Shaggoth now exposes four capability profiles:

```text
reasoning        reason, summarize, classify, plan
local-dev        reasoning + model, workspace files, allowlisted processes, git, artifacts, telemetry
integrations     reasoning + authorized APIs, GitHub, databases, object stores, queues, secrets, schedules,
                 email, calendar, telemetry, artifacts, models, and web search
full-authorized  every supported legitimate capability in the catalog
```

Inspect the catalog:

```bash
shaggoth capabilities
shaggoth capabilities --json
```

Enable the complete supported catalog:

```bash
export SHAGGOTH_CAPABILITY_PROFILE=full-authorized
```

`full-authorized` does **not** mean unrestricted access. Capabilities that touch external resources require an explicit resource scope before the broker dispatches a registered handler. For example, enabling `github.write` does not authorize every repository; the host must grant specific repository scopes.

The supported catalog includes:

```text
reason                 summarize             classify
plan                   model.invoke          fs.read
fs.write               process.run           http.get
http.write             git.read              git.write
github.read            github.write          database.read
database.write         object_store.read     object_store.write
queue.consume          queue.publish         secrets.use
schedule.manage        email.read            email.send
calendar.read          calendar.write        telemetry.read
telemetry.write        artifact.create       artifact.publish
web.search
```

The capability broker is provider-neutral: handlers are registered by the deployment for the systems it actually owns or is authorized to use.

## Open Source Everything catalog

The integration label `gpt-doug-shoggoth-anon-llm` uses the public
`An-anonymous-coder/Open-Source-Everything` catalog as an external software
intelligence source.

The upstream repository is a curated list rather than executable agent code.
Shaggoth therefore indexes its tool names, links, sections, and subsections with
provenance instead of vendoring the upstream README.

The adapter is pinned to upstream release `165.2026.5.13.0`, commit
`7290f2cb9ffa7c7bba1723b7e06f726802de51be`, and records the upstream
`GPL-3.0` license in every generated index.

```bash
shaggoth catalog source
shaggoth catalog refresh
shaggoth catalog search "AI Tools"
shaggoth catalog search "Security Privacy" --limit 10
shaggoth catalog search "Ollama" --json
```

By default the generated cache is written to
`/tmp/shaggoth-catalogs/open-source-everything.json`. Override it with
`SHAGGOTH_OSE_CACHE` or `--cache`. Generated indexes are runtime data and
are not committed to this repository.

See `THIRD_PARTY_SOURCES.md` for attribution and redistribution notes.

## Safety model

The default profile is **offline and non-destructive**. External access, subprocess execution, file writes, credentials, and integrations are disabled unless selected through a capability profile or explicit extra grants.

Scoped capabilities still require their approved resource scope at call time. This prevents a broad profile from silently expanding to unrelated repositories, endpoints, databases, mailboxes, queues, calendars, or storage.

The connector monitor is not a scanner, injection system, stealth agent, or attribution-evasion layer. It performs bounded `GET` checks only against endpoints you explicitly configure. Non-local endpoints must use HTTPS, cross-origin redirects are rejected, responses are size-capped, retries are bounded, and the service identifies itself in normal HTTP headers.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
shaggoth run "Design a resilient swarm scheduler"
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Infrastructure

Shaggoth now includes a deployable infrastructure layer:

- `infra/compose/compose.yml` — hardened single-host API plus optional persistent connector profile.
- `infra/k8s/` — namespace, service account, two-replica deployment, ClusterIP service, HPA, PDB, and default-deny network policies.
- `docs/INFRASTRUCTURE.md` — deployment and network-policy runbook.

Start the local production container stack:

```bash
cp infra/compose/.env.example infra/compose/.env
docker compose --env-file infra/compose/.env -f infra/compose/compose.yml up -d --build
curl http://127.0.0.1:8787/health
```

Render the Kubernetes base:

```bash
kubectl kustomize infra/k8s
```

The Kubernetes base intentionally has no broad external egress. Add only the network ranges or CNI FQDN rules required for the model/API endpoints your deployment is authorized to use.

## Authorized production-style connectors

Configure only systems you own or are explicitly authorized to access:

```bash
export SHAGGOTH_SERVICE_NAME="shaggoth-swarm-gpt100"
export SHAGGOTH_AUTHORIZED_ENDPOINTS="https://api.example.com/health,https://status.example.com/api"
export SHAGGOTH_CONNECT_INTERVAL_SECONDS=30
```

For an approved service using standard bearer authentication:

```bash
export SHAGGOTH_CONNECT_BEARER_TOKEN="<token-from-your-secret-manager>"
```

Poll once:

```bash
shaggoth connect --once
```

Keep the visible foreground monitor running until you stop the process:

```bash
shaggoth connect
```

Each check sends a visible service identity, `X-Client-Service`, and `X-Request-ID`. Events are emitted as structured JSON. Authentication secrets are never printed by the monitor.

## Optional API

```bash
pip install -e '.[api]'
uvicorn shaggoth_swarm.api:app --host 127.0.0.1 --port 8787
```

Operational endpoints:

```bash
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/ready
curl -s http://127.0.0.1:8787/status
curl -s http://127.0.0.1:8787/capabilities
```

## OpenAI-compatible endpoint

The optional adapter can talk to an OpenAI-compatible chat-completions endpoint. It is disabled unless selected explicitly.

```bash
export SHAGGOTH_ADAPTER=openai-compatible
export SHAGGOTH_BASE_URL=https://api.openai.com/v1
export SHAGGOTH_MODEL=<your-model-name>
export OPENAI_API_KEY=<your-key>
shaggoth run "Summarize this architecture"
```

Credentials are read only from environment variables. Never commit `.env` files.

## Architecture

```text
Goal
  |
  v
Orchestrator ----> CapabilityPolicy ----> CapabilityBroker
  |                       |                    |
  v                       v                    v
Planner               Profile + scopes    Registered handlers
  |                                            |
  +----> Agent 001 ----> Model adapter         +--> approved GitHub/API/etc.
  +----> Agent 002 ----> Model adapter
  +----> ...
  +----> Agent 100 ----> Model adapter
  |
  v
Aggregator -> SwarmReport
```

## Repository layout

```text
src/shaggoth_swarm/
  adapters/          model backends
  api.py             optional FastAPI surface
  broker.py          scoped capability dispatcher
  capabilities.py    capability catalog and profiles
  cli.py             command-line entry point
  config.py          environment-driven config
  connectors.py      authorized endpoint monitor
  models.py          typed swarm data structures
  orchestrator.py    planning, routing, aggregation
  policy.py          capability profile and scope policy
  registry.py        deterministic 100-agent registry
```

## Design principles

1. **Broad capability, narrow authority** — the catalog can be large while each resource remains scoped.
2. **Bounded autonomy** — fanout and depth are capped.
3. **Explicit capabilities** — profiles and per-resource scopes are visible.
4. **Auditable execution** — tasks, connector requests, and capability grants are observable.
5. **Replaceable providers** — the broker isolates service-specific handlers.
6. **Authorized connectivity only** — integrations are limited to configured systems and scopes.
7. **Normal service identity** — no spoofing, stealth headers, or log suppression.

## License

MIT
