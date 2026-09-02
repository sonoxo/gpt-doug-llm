# FRONTLINE AGENTIC WORKFLOW

## AIP + SHADOW GLASS + THE BLACK HOUSE

This workflow is the mission-support extension of [`AIP_AGENTIC_WORKFLOWS.md`](../AIP_AGENTIC_WORKFLOWS.md). It inserts a compliance/build-authorization gate before agents may generate deployable code, call consequential tools, expose controlled data to a model, or release a field-facing capability.

```text
MISSION REQUEST
   ↓
THE BLACK HOUSE INTAKE
   ↓
FRONTLINE BUILD MANIFEST
   ↓
SHADOW GLASS COMPLIANCE PREFLIGHT
   ├─ mission/use-case
   ├─ data classification
   ├─ contract/CMMC
   ├─ export jurisdiction
   ├─ clearance/program access
   ├─ environment authorization
   └─ model/data-egress authorization
   ↓
GREEN? ── NO → AMBER REVIEW / RED DENY / BLACK QUARANTINE
   │
  YES
   ↓
AIP AGENT PLAN
   ↓
ONTOLOGY / DATA RETRIEVAL
   ↓
CODE / LOGIC / ACTION / AUTOMATION DESIGN
   ↓
GLASS ONION TOOL + EXECUTION OBSERVABILITY
   ↓
TESTS + SECURITY CHECKS + AIP EVALS
   ↓
HUMAN REVIEW WHEN REQUIRED
   ↓
DEPLOYMENT AUTHORIZATION
   ↓
FIELD RELEASE
   ↓
MONITOR → AUDIT → ROLLBACK / REVOKE
```

## Workflow contract

### 01 — Intake

The Black House creates a mission record with a clear operational problem, intended users, expected outcome, owner, technical owner, and known constraints.

### 02 — Compliance manifest

Create a manifest compatible with [`../schemas/frontline-build-manifest.schema.json`](../schemas/frontline-build-manifest.schema.json).

No agent may infer missing legal/security authority as `true`. Unknown authority remains `UNKNOWN`/`AMBER` until an authorized program source supplies evidence.

### 03 — Data handling determination

Classify each input as `PUBLIC`, `INTERNAL`, `FCI`, `CUI`, `CUI_CTI`, `EXPORT_CONTROLLED`, `CLASSIFIED`, or `UNKNOWN`.

The data label is inherited by derived artifacts unless an authorized declassification/decontrol/public-release decision says otherwise.

### 04 — Contract / CMMC gate

If a DoD solicitation/contract requires CMMC, record the exact required status/level and system boundary. Do not guess a level from the phrase “defense project.”

### 05 — Export-control gate

Determine whether the item/software/service/technical data is ITAR-controlled, EAR-controlled, public-domain/excluded, not applicable, or unresolved. Foreign-person/model/provider access remains blocked until recipient authorization is established where required.

### 06 — Classified-work gate

Classified data or mission logic is blocked from normal GitHub, consumer SaaS, public model endpoints, and ordinary local development. It requires an explicitly authorized program and accredited environment. Clearance/facility requirements come from the sponsoring program and security authority.

### 07 — Model boundary gate

Run both:

- [`../policies/external-model-egress.rego`](../policies/external-model-egress.rego)
- [`../policies/frontline-tool-compliance.rego`](../policies/frontline-tool-compliance.rego)

Outside-model egress for CUI/export-controlled/classified material is deny-by-default.

### 08 — Agent plan

The agent may plan only within the approved mission lane, tools, data objects, environment, and time/budget constraints.

### 09 — Build lane

Approved examples include logistics, readiness, maintenance, defensive cyber, authorized intelligence briefing, search/knowledge management, communications support, geospatial visualization, rescue/medical support, sensor health, training, simulation, and evaluation.

This workflow does not authorize autonomous target selection, autonomous weapon release/fire control, or unrestricted offensive cyber operations.

### 10 — Validation

Require evidence appropriate to the tool:

- unit/integration tests;
- schema and ontology validation;
- negative security tests;
- data-egress tests;
- prompt-injection/tool-abuse tests for agentic systems;
- AIP-style evals for model quality/grounding;
- rollback/kill-switch test;
- audit/lineage verification.

### 11 — Human authority

Material external actions, elevated-impact changes, exceptions, and unresolved AMBER states require a named human/program authority. Approval must be recorded and expire or be scoped to the release.

### 12 — Release

A field release must identify version, environment, owners, approved users, data classes, model/provider versions, tool scopes, validation evidence, rollback behavior, and audit receipt.

## CI / deterministic enforcement

GitHub workflow: [`../../.github/workflows/frontline-compliance-gate.yml`](../../.github/workflows/frontline-compliance-gate.yml)

Local preflight:

```bash
python scripts/frontline_compliance_check.py safety-shield/manifests/frontline-tool.example.json
```

Expected states:

- `GREEN` — build may proceed within the manifest scope;
- `AMBER` — stop and obtain missing compliance/program evidence;
- `RED` — deny the requested build/deploy path;
- `BLACK` — quarantine and invoke incident response.

## Decision principle

> **The model may reason about the mission. Only verified authority may unlock the mission.**

Compliance is therefore part of the agent state machine, not a PDF reviewed after development.
