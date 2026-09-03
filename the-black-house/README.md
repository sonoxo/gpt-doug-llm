# THE BLACK HOUSE // KERNEL 3.0.0

Canonical governance, ontology, identity, mission-routing, evidence, telemetry, and command-center root for the Sonoxo agentic ecosystem.

**Phases 1–8 implementation status:** code-complete. Phases 4–8 add the executable RVIA mission bus, durable mission/evidence history, live GitHub fleet telemetry, Palantir verification truth states, and the Black House Command Center on VA3LM port `8088`.

> Phase 7 has an external dependency: repository implementation is complete, but a Palantir environment is **not** labeled `LIVE_TENANT_VERIFIED` until an authorized tenant probe succeeds. Code completeness never implies tenant entitlement.

## Authority

This directory is the machine-readable global root for ecosystem identity, service registration, agent registration, mission envelopes, ontology contracts, kernel vocabulary, routing policy, telemetry contracts, governance boundaries, phase status, and control-plane validation.

It does **not** duplicate every service implementation. Each registered component remains owned by its source repository and is referenced here through Black House contracts.

`XuniaDAO` remains the **XUNIAverse domain root**. It is not the global Black House control-plane root. `ZYRA` remains the security/approval/audit authority for registered mutation paths. External platforms remain authoritative for their own credentials, permissions, tenants, and approvals.

## Current phase status

| Phase | Capability | State |
|---|---|---|
| 1 | Foundation / CI stabilization | `COMPLETE` |
| 2 | Black House control-plane root | `COMPLETE` |
| 3 | Canonical kernel + ontology | `COMPLETE` |
| 4 | RVIA universal mission router | `COMPLETE` |
| 5 | Mission History + evidence ledger | `COMPLETE` |
| 6 | Live ecosystem telemetry | `COMPLETE` |
| 7 | Palantir verification plane | `CODE_COMPLETE`; live tenant state is probe-derived |
| 8 | Black House Command Center | `COMPLETE` |

The machine-readable source is `status/phases.json`.

## Kernel 3.0.0

The executable kernel is defined by:

- `kernel/kernel.manifest.json` — canonical kernel version, object types, relationships, invariants, and consumer bindings.
- `kernel/kernel.schema.json` — machine schema for the kernel manifest.
- `ontology/ontology.schema.json` — canonical ontology vocabulary, locked to kernel `3.0.0`.
- `../scripts/black_house_kernel.py` — executable fail-closed kernel loader and validator.
- `../scripts/validate_black_house.py` — whole-control-plane contract and drift validator.

Canonical object vocabulary includes `Mission`, `Agent`, `Model`, `Repository`, `Service`, `Tool`, `Evidence`, `Decision`, `Approval`, `Action`, `Deployment`, `Incident`, `Policy`, `Artifact`, and related operational objects.

Canonical relationships are:

```text
EXECUTES · USES · PRODUCES · DERIVED_FROM · AUTHORIZES · GOVERNS
DEPLOYED_TO · IMPLEMENTS · RUNS_ON · ROUTES_TO · AUDITS · EVIDENCES
```

Kernel invariants are fail-closed: typed objects, registered relationships, evidence provenance, explicit approval for consequential mutation, runtime health before GREEN, and no implied external authorization.

## Phase 4 — RVIA universal mission router

Runtime implementation: `va3lm/src/va3lm/rvia.py`.

Canonical protocol: `black-house-mission-v1`.

```text
MISSION
  ↓
RVIA
  ↓
IDENTITY
  ↓
SHADOW GLASS
  ↓
ONTOLOGY CONTEXT
  ↓
PLANNER
  ↓
ZYRA AUTHORIZATION
  ↓
DISPATCH
  ↓
GLASS ONION
  ↓
EVIDENCE
  ↓
AUDIT
```

The router fails closed on unknown targets, unknown classifications, missing required capabilities, denied approvals, and consequential mutation without explicit `APPROVED` state.

Registered mission targets are:

`GPT_DOUG_MAX`, `VIRGINIA`, `WAKEUP3LM`, `ZYRA`, `XUNIA`, `NXYZ`, `ZYRA_CLOUD`, `AIP_REGISTRY`, and `PALANTIR`.

Cross-repo mission bindings are stored at:

- `sonoxo/xuniadao/.black-house/mission-router.json`
- `sonoxo/zyra/.black-house/mission-router.json`
- `sonoxo/aip-community-registry-zyra/.black-house/mission-router.json`

Canonical router contract: `missions/router.manifest.json`.

## Phase 5 — Mission History + evidence ledger

Runtime implementation: `va3lm/src/va3lm/mission_ledger.py`.

The ledger uses SQLite and records:

- mission envelope;
- request identity;
- target and classification;
- approval state;
- Shadow Glass policy event;
- ontology context event;
- Zyra authorization event;
- adapter result;
- Glass Onion route evidence;
- final mission status;
- ordered audit timeline.

Default local path:

```text
.black-house/mission-history.db
```

Override with `BLACK_HOUSE_LEDGER_PATH`.

Canonical record schema: `missions/history.schema.json`.

## Phase 6 — Live ecosystem telemetry

Runtime implementation: `va3lm/src/va3lm/ecosystem_telemetry.py`.

The collector reads current GitHub repository metadata and the latest workflow state for the registered core fleet. Default monitored repositories are:

- `sonoxo/gpt-doug-llm`
- `sonoxo/xuniadao`
- `sonoxo/zyra`
- `sonoxo/aip-community-registry-zyra`

Telemetry explicitly distinguishes `GREEN`, `AMBER`, and `RED` workflow states and reports whether a repository was actually reachable. A deterministic `live=false` mode is available for offline tests.

Canonical schema: `telemetry/telemetry.schema.json`.

## Phase 7 — Palantir verification plane

The repository already contains Foundry/Ontology, AIP, Gotham, Apollo, Automate, and tenant-probe adapters. Phase 7 adds a Black House truth-state wrapper at `va3lm/src/va3lm/palantir_status.py`.

Allowed verification states are:

- `PROBE_UNAVAILABLE_IN_STANDALONE_RUNTIME`
- `LIVE_TENANT_UNVERIFIED`
- `CONFIGURED_BUT_NOT_FULLY_VERIFIED`
- `LIVE_TENANT_VERIFIED`

The Black House never derives `LIVE_TENANT_VERIFIED` from code presence, environment-variable presence, licensing assumptions, or repository credentials. A successful authorized probe is required.

Canonical schema: `integrations/palantir/status.schema.json`.

## Phase 8 — Black House Command Center

The command center is mounted into the existing VA3LM FastAPI runtime.

Start VA3LM on its canonical port:

```bash
va3lm serve --host 127.0.0.1 --port 8088
```

Open:

```text
http://127.0.0.1:8088/black-house
```

The surface includes:

- phases 1–8 status;
- RVIA mission console;
- durable Mission History;
- live GitHub fleet telemetry;
- Palantir verification truth state;
- RVIA router manifest.

Runtime APIs:

```text
GET  /api/black-house/status
GET  /api/black-house/router
POST /api/black-house/missions
GET  /api/black-house/missions
GET  /api/black-house/missions/{mission_id}
GET  /api/black-house/telemetry?live=true
GET  /api/black-house/palantir
GET  /black-house
```

## Bound execution planes

| Plane | Kernel / mission binding | Role |
|---|---|---|
| **GPT-DOUG-LLM MAX / Black House** | canonical | planning, orchestration, kernel authority |
| **VA3LM :8088** | `va3lm/src/va3lm/ontology.py` + RVIA runtime | mission bus + bounded execution + command center |
| **Wakeup3lm** | `wakeup3lm/ontology.py` | IDE-native object/link execution state |
| **XUNIA** | `.black-house/kernel.json` + `.black-house/mission-router.json` | XUNIAverse domain ontology + agents |
| **ZYRA / NXYZ / Zyra Cloud** | `.black-house/kernel.json` + `.black-house/mission-router.json` | policy, approval, evidence, cloud execution |
| **AIP quality plane** | `.black-house/runtime.json` + `.black-house/mission-router.json` | reusable CI/security quality plane |
| **Palantir adapters** | authorized external adapter | optional tenant execution after verification |

## Canonical files

- `ecosystem.yaml` — root system manifest.
- `registry/repositories.json` — authoritative repository registry.
- `registry/services.json` — runtime/service registry.
- `registry/agents.json` — agent/model execution registry.
- `missions/mission.schema.json` — universal mission envelope.
- `missions/router.manifest.json` — RVIA routing contract.
- `missions/history.schema.json` — durable mission-history record.
- `ontology/ontology.schema.json` — canonical object/link vocabulary.
- `kernel/kernel.manifest.json` — executable kernel contract.
- `kernel/kernel.schema.json` — kernel manifest schema.
- `runtime/runtime-contract.json` — runtime health contract.
- `telemetry/telemetry.schema.json` — live fleet telemetry contract.
- `integrations/palantir/status.schema.json` — Palantir verification truth-state contract.
- `status/phases.json` — phases 1–8 implementation state.
- `governance/CONTROL-PLANE.md` — execution and authority boundary.

## Full-completion CI contract

`.github/workflows/gpt-doug-max-full-completion.yml` must fail closed unless it proves:

1. canonical Black House contracts validate;
2. kernel self-check passes;
3. RVIA routes local and cross-repo contract targets;
4. mutation approval gates fail closed;
5. Mission History persists evidence and ordered audit events;
6. VA3LM tests/lint/security/compile pass;
7. live port `8088` exposes Black House status, router, and command-center routes;
8. XUNIA builds/tests and accepts `black-house-mission-v1`;
9. ZYRA tests/typecheck/audit/build and accepts the mission protocol for ZYRA/NXYZ/Zyra Cloud;
10. AIP quality plane accepts the same mission protocol;
11. kernel and mission-protocol coherence pass across repositories;
12. telemetry collector contract passes and a live GitHub fleet probe is attempted;
13. Palantir adapter/probe tests pass while tenant status remains truthfully probe-derived;
14. final verdict fails closed unless every repository-controlled critical plane is GREEN.

## State language

Use these lifecycle distinctions when reporting system status:

`planned`, `implemented`, `ci_verified`, `deployed`, `platform_access`, `authorized_action`, `third_party_approved`.

Implementation never implies deployment. Credentials never imply authorization. Adapter code never implies a live tenant. External verification is reported separately from repository completion.
