# Atomic Layers

Shaggoth's atomic architecture separates execution into eight composable layers.
Each layer has an explicit contract, dependency boundary, and invariants.

| Layer | Name | Responsibility |
| ---: | --- | --- |
| 0 | particle | immutable IDs, timestamps, envelopes, hashes, typed state |
| 1 | atom | one scoped capability invocation |
| 2 | molecule | bounded composition of capability atoms |
| 3 | cell | one agent identity and execution lifecycle |
| 4 | swarm | bounded multi-agent coordination and aggregation |
| 5 | service | API, queues, storage, catalogs, and connectors |
| 6 | fabric | containers, Kubernetes, network policy, scaling, health |
| 7 | governance | policy, audit, provenance, risk, and compliance assertions |

## Transition model

Execution promotes upward one layer at a time:

```text
particle -> atom -> molecule -> cell -> swarm -> service -> fabric
    \        \          \       \       \         \        \
     +--------+----------+-------+-------+---------+-------> governance
```

Any execution layer can emit a governance record. Governance records cannot
silently re-enter the execution stack.

## Atomic envelope

`AtomicEnvelope` gives every unit:

- unique object ID
- shared trace ID across promotions
- parent ID
- timestamp
- payload digest
- explicit current layer

This lets a capability call, agent result, service event, or deployment event be
traced back to the particle that created it.

## CLI

```bash
shaggoth layers
shaggoth layers --json
shaggoth layers --validate
```

## API

```text
GET /layers
```

The layer graph does not widen permissions. Capability policy, scopes, network
policy, and deployment controls remain authoritative at their respective layers.
