# Palantir Full Stack — XUNIA / GPT-DOUG-MAX

## Status

The repository now models the Palantir product stack as an explicit set of ecosystem planes rather than treating Foundry/Ontology as the whole integration.

| Capability | Ecosystem plane | Code status | Live tenant status |
| --- | --- | --- | --- |
| Foundry | governed data / transform plane | ✅ Implemented | Requires authorized enrollment credentials |
| Ontology | semantic operational source of truth | ✅ Implemented | Requires ontology/object/action permissions |
| AIP provider-compatible model invocation | reasoning / orchestration plane | ✅ Implemented | Requires AIP enabled + selected model entitlement |
| Published AIP Logic / Function invocation | reasoning / workflow plane | ✅ Implemented | Requires published query/function + permission |
| AIP evaluation regression runner | evaluation plane | ✅ Implemented | Executes real published Logic targets through Foundry API; does not create AIP Evals UI resources |
| Automate Action / AIP Logic effect bridge | event workflow plane | ✅ Implemented | Trigger/condition resource remains configured in Palantir Automate |
| Gotham REST adapter | mission operational-picture plane | ✅ Implemented | Requires authorized Gotham endpoint + OAuth/Bearer identity |
| Defense OSDK contract | typed defense application plane | ✅ Implemented local capability gate | Requires tenant-generated OSDK client/types + domain permissions |
| Apollo GraphQL adapter | release / deployment plane | ✅ Implemented | Requires Apollo Hub GraphQL endpoint + token |
| Apollo Product Release publish | release / deployment plane | ✅ Implemented | Requires `apollo-cli`, Apollo credentials, valid product package and explicit approval |
| JupyterLab / Code Workspace routing contract | engineering / analysis plane | ✅ Implemented | Workspace provisioning is performed in the Foundry enrollment |
| Live tenant entitlement verification | verification plane | ✅ Verifier implemented | Run `/palantir probe` or `/palantir probe-model` with authorized credentials |
| Wakeup3lm → AIP invocation + Ontology audit | reasoning + state plane | ✅ Implemented | Requires Foundry/AIP tenant configuration |

## XUNIA ecosystem architecture

```text
AUTHORIZED / REPRESENTATIVE SOURCES
              │
              ▼
      PALANTIR FOUNDRY
  ingestion • transforms • lineage
              │
              ▼
        FOUNDRY ONTOLOGY
 objects • links • actions • functions
              │
      ┌───────┼─────────┐
      │       │         │
      ▼       ▼         ▼
     AIP    GOTHAM   DEFENSE OSDK
 reasoning  mission   typed apps
 workflows  picture   + domain SDK
      │       │         │
      └───────┼─────────┘
              ▼
          AUTOMATE
 event/time conditions + bounded effects
              │
      ┌───────┴────────┐
      ▼                ▼
 JUPYTERLAB          APOLLO
 analysis/dev      release/deploy
      │                │
      └───────┬────────┘
              ▼
 XUNIA / ZYRA / RVIA / HOLO / HOUSES
```

## Product-to-role routing

- **Foundry** — governed ingestion, transformation, lineage and application data.
- **Ontology** — governed operational nouns and verbs: objects, links, properties, Actions and Functions.
- **AIP** — LLM/model reasoning, Logic workflows, agent orchestration and evaluation.
- **Gotham** — authorized defense/intelligence operational view over supported objects and markings.
- **Defense OSDK** — typed application layer for authorized intelligence, mission-planning, order-of-battle and sustainment workflows.
- **Automate** — event/time conditions and bounded effects through Ontology Actions or AIP Logic.
- **JupyterLab Code Workspaces** — analysis, notebooks, models and engineering workflows.
- **Apollo** — product release, delivery and deployment governance.

## Defense OSDK safety boundary

The local capability contract exposes these domains when a tenant-generated OSDK client is actually provisioned:

- intelligence
- mission planning
- order of battle
- sustainment

`targeting-and-fires` can be represented as read-only ontology/simulation context where the operator is authorized, but the local GPT-DOUG/XUNIA integration does **not** expose autonomous weapon-targeting, fires execution or weapons-release authority.

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
- Defense OSDK tenant-generated application types/client contract.
- Apollo Hub GraphQL API and `apollo-cli product-release create` flow.
- Automate-compatible effects using Foundry Actions and AIP Logic execution.

## Safety and authority

- HTTPS and exact-host pinning for Foundry/Gotham transport.
- No secrets committed to source.
- Writes disabled by default.
- Consequential Actions require explicit human approval at the calling layer.
- Apollo publishing requires explicit `approve=True`.
- Defense OSDK configuration never creates mission authority.
- No autonomous local targeting-and-fires execution.
- No Palantir entitlement, government affiliation, ATO, classification authority or certification is inferred from repository configuration.


## Runtime environment lifecycle architecture watch

The operator-supplied USPTO Patent Public Search record for **US-12748581-B2, _Systems and methods to automatically create runtime environments_** is retained as a provenance-aware architecture watch. The supplied detailed record identifies Palantir Technologies Inc. in Applicant and Assignee fields.

The source-supported lifecycle is:

```text
environment request
  -> environment metadata / ownership / template
  -> manifest + resource configuration
  -> backing cluster / node provisioning
  -> software-product deployment
  -> runtime operator state loop
  -> deploy | upgrade | rollback
  -> verification
  -> expiration / destruction
```

The source also describes GUI inputs for environment name/description, owner/co-owner, template, release channels/overrides, expiration, node count and cost visibility; runtime-operator authentication; local/cloud node options; capacity gates; and cost/subscription-sensitive lifecycle decisions.

**XUNIA / GPT-DOUG mapping:** versioned environment templates, manifest-driven isolated sandboxes, explicit ownership/provenance, runtime state observation, policy-gated upgrades/rollbacks, TTL cleanup, capacity/cost controls and human approval before consequential production changes.

This is a **research and independent-design watch**, not a claim that Foundry/Apollo exposes this exact patent implementation to the configured tenant, and not legal or freedom-to-operate advice.

Source objects:
- `intel/sources/uspto-palantir-attributed-US-12748581-B2.json`
- `intel/sources/uspto-palantir-maven-query-2026-09-29.json`
- `intel/briefings/2026-09-29-uspto-palantir-runtime-environments.md`
