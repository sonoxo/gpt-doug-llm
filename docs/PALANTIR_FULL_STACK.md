# Palantir Full Stack — Wakeup3lm / GPT-DOUG-MAX

## Status

Repository implementation status is now green across the previously incomplete Palantir planes.

| Capability | Code status | Live tenant status |
| --- | --- | --- |
| Foundry / Ontology REST | ✅ Implemented | Requires authorized enrollment credentials |
| AIP provider-compatible model invocation | ✅ Implemented | Requires AIP enabled + selected model entitlement |
| Published AIP Logic / Function invocation | ✅ Implemented | Requires published query/function + permission |
| AIP evaluation regression runner | ✅ Implemented | Executes real published Logic targets through Foundry API; does not create AIP Evals UI resources |
| Automate Action / AIP Logic effect bridge | ✅ Implemented | Trigger/condition resource remains configured in Palantir Automate |
| Gotham REST adapter | ✅ Implemented | Requires authorized Gotham endpoint + OAuth/Bearer identity |
| Apollo GraphQL adapter | ✅ Implemented | Requires Apollo Hub GraphQL endpoint + token |
| Apollo Product Release publish | ✅ Implemented | Requires `apollo-cli`, Apollo credentials, valid product package and explicit approval |
| JupyterLab / Code Workspace routing contract | ✅ Implemented | Workspace provisioning is performed in the Foundry enrollment |
| Live tenant entitlement verification | ✅ Verifier implemented | Run `/palantir probe` or `/palantir probe-model` with authorized credentials |
| Wakeup3lm → AIP invocation + Ontology audit | ✅ Implemented | Requires Foundry/AIP tenant configuration |

## Runtime architecture

```text
GPT-DOUG-MAX
    │
    ▼
Wakeup3lm IDE LLM
    │
    ├── Local Wakeup3lm Ontology / audit
    │
    ▼
Palantir AIP Client
    ├── OpenAI-compatible AIP model proxy
    ├── Anthropic-compatible AIP model proxy
    ├── Published AIP Logic / Function Queries
    └── External CI eval suites against published Logic
    │
    ▼
Foundry Ontology
    ├── Objects
    ├── Searches
    ├── Query execution
    └── Human-gated Actions
    │
    ├── Automate effects
    ├── Gotham REST
    └── Apollo GraphQL / Product Release publishing
```

## Commands

- `/palantir stack` — code/configuration map.
- `/palantir probe` — live Foundry, Logic target, Gotham and Apollo readiness without executing an AIP model.
- `/palantir probe-model` — explicitly send a minimal request through the configured AIP model proxy.
- `/palantir query-types <ontology>` — list published Query/Logic targets.
- `/palantir aip-logic <ontology> <query_api_name> <parameters_json>` — execute a published AIP Logic/function query.
- `/palantir aip-chat <model_rid> <prompt>` — call an AIP-enabled model through the Foundry OpenAI-compatible proxy.

## What “green” means

A green code status means the adapter, permission gate, tests, runtime routing and failure behavior exist in this repository. It does **not** mean the repository owns a Palantir license, has access to a particular government environment, or can bypass tenant permissions. Live tenant verification is deliberately separate and machine-readable.

## Public Palantir API surfaces used

- Foundry Ontology API v2.
- Ontology Query execution for published Functions / AIP Logic.
- AIP provider-compatible LLM proxy endpoints.
- Gotham REST API under `/api/gotham/v1`.
- Apollo Hub GraphQL API and `apollo-cli product-release create` flow.
- Automate-compatible effects using Foundry Actions and AIP Logic execution.

## Safety and authority

- HTTPS and exact-host pinning for Foundry/Gotham transport.
- No secrets committed to source.
- Writes disabled by default.
- Consequential Actions require explicit human approval at the calling layer.
- Apollo publishing requires explicit `approve=True`.
- No Palantir entitlement, government affiliation, ATO, classification authority or certification is inferred from repository configuration.
