# XUNIA Platform + AIP

XUNIA Platform is a clean-room, original full-stack ontology and agentic operations console for the XUNIA ecosystem. It does not copy proprietary Palantir source code, private APIs, branding, or UI assets.

## Included

- ontology object + relationship store
- ontology search and neighborhood traversal
- AIP model gateway with local fallback
- agent registry
- bounded tool registry
- execution planning
- per-tool risk classification
- human approval gates
- AIP execution audit trail
- SONOXO telemetry connector
- XUNIA Chain integration configuration
- original browser console for Overview, Ontology, AIP, Operations, and Audit
- HTTP API
- Node tests
- Docker packaging

## Run

```bash
cd xunia-platform
npm install
npm run build
npm test
npm start
```

Open `http://127.0.0.1:4400`.

## AIP flow

```text
user prompt
  -> selected agent
  -> ontology grounding
  -> model gateway
  -> proposed tool plan
  -> agent allowlist
  -> risk / approval policy
  -> tool execution
  -> audit record
  -> response + execution plan
```

## Environment

```bash
XUNIA_PLATFORM_HOST=127.0.0.1
XUNIA_PLATFORM_PORT=4400
XUNIA_CHAIN_URL=http://127.0.0.1:4317
SONOXO_URL=http://127.0.0.1:3001/api/sonoxo/harvest

# Optional external model gateway. If omitted, AIP uses its deterministic local fallback.
XUNIA_MODEL_URL=
XUNIA_MODEL_TOKEN=
```

The model gateway expects JSON `{ system, message, context }` and accepts a response containing one of `text`, `response`, or `output`.

## API

### Platform

- `GET /health`
- `GET /api/platform/status`

### Ontology

- `GET /api/ontology`
- `GET /api/ontology/search?q=...&type=...`
- `POST /api/ontology/objects`
- `POST /api/ontology/links`

Example object:

```json
{
  "id": "service:example",
  "type": "Service",
  "properties": { "name": "Example" }
}
```

Example link:

```json
{
  "id": "link:example-host",
  "type": "HOSTS",
  "from": "zone:virginia-local",
  "to": "service:example",
  "properties": {}
}
```

### AIP

- `GET /api/aip/agents`
- `GET /api/aip/tools`
- `POST /api/aip/run`
- `POST /api/aip/runs/:runId/approve/:stepId`
- `GET /api/aip/audit`

Run request:

```json
{
  "agentId": "xunia-analyst",
  "message": "Analyze service:sonoxo and its connected objects.",
  "contextIds": ["service:sonoxo"]
}
```

## AIP controls

Agents can only call tools present in both the global registry and that agent's allowlist. Tools have `low`, `medium`, or `high` risk. Each agent declares which risk levels require explicit approval. All tool execution, blocked tools, approval requirements, failures, and completed runs are added to the audit trail.

## Docker

```bash
docker build -t xunia-platform .
docker run --rm -p 4400:4400 xunia-platform
```

## Architecture

```text
Browser Console
      |
      v
XUNIA Platform API
  |       |       |
  |       |       +--> Audit
  |       +----------> AIP Engine
  |                       |
  |                       +--> Model Gateway
  |                       +--> Tool Registry
  |                       +--> Approval Gate
  |                       +--> SONOXO
  +------------------> Ontology
                           |
                           +--> XUNIA services / chain objects
```
