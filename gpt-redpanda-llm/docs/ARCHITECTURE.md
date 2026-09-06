# GPT-REDPANDA Architecture

## Role

GPT-REDPANDA is the local edge/operator node in the Sonoxo / XUNIA ecosystem. It is designed to remain useful when cloud services are unavailable and to connect outward only through explicit adapters.

```text
Operator
  |
  v
GPT-REDPANDA Portal
  |-- Local LLM
  |-- Cyber CPR
  |-- Terminal metadata watcher
  |-- ZYRA File Intelligence
  |-- Task queue (planned)
  |
  +--> GitHub adapter
  +--> Google Drive adapter
  +--> Gmail adapter
  +--> XUNIA ontology adapter
  +--> Palantir adapter (only when authorized)
```

## Trust zones

### Zone A — Local node

USB-resident runtime, local state, local logs, local models, and operator UI.

### Zone B — Controlled external integrations

GitHub, Drive, Gmail, or other services. Each adapter must have a separate token/authorization boundary and observable connection state.

### Zone C — Public publication

Only artifacts explicitly promoted to `PUBLIC_RELEASE` may enter the public GitHub/web publication plane.

### Zone D — Restricted systems

Officially classified material never crosses into the ordinary Red Panda/GitHub/consumer-cloud path. Restricted-but-unclassified material remains review-gated.

## Core principles

1. Local-first execution.
2. Explicit permissions.
3. Evidence-backed state reporting.
4. Bounded repair instead of uncontrolled mutation.
5. Provenance for every imported file or external datum.
6. Separate implementation, deployment, connectivity, and authorization states.
7. No command-text keylogging; terminal watch stays metadata-only unless the operator explicitly chooses another design in a controlled environment.

## Extension interface

Every new capability should expose:

- `name`
- `version`
- `read_scopes`
- `write_scopes`
- `health_check()`
- `execute()`
- `audit_event()`
- `connection_state`
- `authorization_state`

Adapters should fail closed for writes and degrade gracefully for reads.
