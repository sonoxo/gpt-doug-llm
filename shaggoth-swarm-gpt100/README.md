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

## Safety model

The default profile is **offline and non-destructive**. Network access, shell execution, filesystem writes outside a workspace, credential access, self-replication, and unbounded task creation are not granted by default. Tool capabilities must be explicitly allowlisted by the host application.

The connector monitor is not a scanner, injection system, stealth agent, or attribution-evasion layer. It performs bounded `GET` checks only against endpoints you explicitly configure. Non-local endpoints must use HTTPS, cross-origin redirects are rejected, responses are size-capped, retries are bounded, and the service identifies itself in normal HTTP headers.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
shaggoth run "Design a resilient swarm scheduler"
```

Run with the built-in mock adapter and 100 agents:

```bash
SHAGGOTH_AGENT_COUNT=100 shaggoth run "Map the work into parallel research tracks"
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

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

Default retry behavior is limited to two retries for transient transport errors and HTTP 429/5xx responses, using exponential backoff. The polling interval cannot be set below five seconds.

The monitor does not discover endpoints, scan address ranges, submit arbitrary payloads, suppress logs, spoof unrelated software, or modify remote systems.

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
```

Run a swarm job:

```bash
curl -s -X POST http://127.0.0.1:8787/v1/swarm/run \
  -H 'content-type: application/json' \
  -d '{"goal":"Create a launch checklist","fanout":8}'
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
Orchestrator ----> Policy Gate
  |                  |
  v                  v
Planner         Capability decision
  |
  +----> Agent 001 ----> Model adapter
  +----> Agent 002 ----> Model adapter
  +----> ...
  +----> Agent 100 ----> Model adapter
  |
  v
Aggregator -> SwarmReport

Authorized endpoints
  |
  v
Exact allowlist
  |
  v
Visible service identity -> optional bearer auth -> bounded GET probe
  |
  v
Bounded retry/backoff -> structured JSON audit event
```

## Repository layout

```text
src/shaggoth_swarm/
  adapters/          model backends
  config.py          environment-driven config
  connectors.py      authorized endpoint monitor
  models.py          typed swarm data structures
  policy.py          capability allowlist
  registry.py        deterministic 100-agent registry
  orchestrator.py    planning, routing, aggregation
  cli.py             command-line entry point
  api.py             optional FastAPI surface
```

## Design principles

1. **Bounded autonomy** — fanout and depth are capped.
2. **Explicit capabilities** — deny by default.
3. **Local-first** — the default adapter performs no network calls.
4. **Auditable execution** — every task and result has an ID and timestamp.
5. **Replaceable models** — adapters isolate model-provider details.
6. **No self-propagation** — the framework does not clone itself, scan networks, or modify external systems on its own.
7. **Authorized connectivity only** — persistent monitoring is limited to explicitly configured endpoints.
8. **Normal service identity** — no spoofing, stealth headers, or log suppression.

## License

MIT
