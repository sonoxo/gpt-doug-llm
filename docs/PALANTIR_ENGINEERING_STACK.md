# GPT-DOUG Palantir Engineering Stack

This is a clean-room engineering knowledge layer derived from public Palantir Learn links supplied by the project owner and corroborated against public Palantir Foundry documentation. It does not copy certification-guide text, proprietary code, private APIs, or Palantir product assets.

## Sources

- Data Engineer guide: https://learn.palantir.com/data-engineer-guide/1388785
- Application Developer guide: https://learn.palantir.com/application-developer-guide/1481796
- Public Foundry pipeline, data expectations, ontology, application-building, Workshop, and AIP documentation referenced in `workers/knowledge/palantir_engineering_stack.jsonl`.

## Stacked architecture

```text
SOURCE / INTAKE
    ↓
DATA CONNECTION + PROVENANCE
    ↓
NORMALIZE / TRANSFORM
    ↓
DATA EXPECTATIONS + QUALITY GATE
    ↓
CANONICAL DATA PRODUCTS
    ↓
ONTOLOGY
objects • properties • links • actions
    ↓
APPLICATION LAYER
workflow • variables • events • UI • APIs
    ↓
AIP / LLM LAYER
bounded context • semantic retrieval • functions • governed actions
    ↓
HUMAN / POLICY APPROVAL
    ↓
RELEASE + HEALTH + LINEAGE + AUDIT
```

## Agentic fleet

Complex missions are decomposed into bounded specialist roles rather than handing an unrestricted execution surface to one model.

| Role | Responsibility |
| --- | --- |
| Intake | Source inventory, provenance, constraints, ownership, outcomes |
| Pipeline | Ingestion, normalization, transforms, publication, freshness |
| Quality | Preconditions, postconditions, tests, integrity, fail policy |
| Ontology | Canonical objects, properties, links, actions, semantic contracts |
| Application | Lowest-complexity workflow/UI/API surface that meets the need |
| Security | Least privilege, secrets, write boundaries, abuse cases |
| Release | CI, health, downstream impact, rollback, promotion evidence |
| Observer | Lineage, evidence, unresolved risk, execution status, audit |

The deterministic planner is `workers/engineering_fleet.py`.

## Decision loop

```text
INSPECT
  → MODEL
  → PLAN
  → DECOMPOSE
  → EXECUTE
  → VALIDATE
  → OBSERVE
  → REPAIR
  → APPROVE
  → RELEASE
  → AUDIT
```

Independent checks may run in parallel, but dependencies and write gates stay explicit. High-impact external actions, production release, destructive changes, credentials, or payment-related operations require the surrounding runtime's applicable approval policy.

## Data-engineering operating principles

1. Work backward from the target operational ontology and workflow.
2. Separate source cleanup, reusable transforms, canonical/ontology outputs, and consuming workflows.
3. Publish stable datasets with ownership, schema, freshness, and downstream contracts.
4. Encode critical assumptions as executable expectations and abort bad builds before propagation.
5. Use batch by default when sufficient; adopt incremental or streaming only when scale/latency requirements justify added complexity.
6. Treat lineage, health, build history, and ownership as production features.
7. Review downstream blast radius before changing production contracts.

## Application-development operating principles

1. Design from ontology objects, links, properties, and governed actions before UI details.
2. Use the lowest-complexity application surface that meets the workflow.
3. Treat widgets/components as explicit input/output units connected by typed state and events.
4. Route domain mutations through governed actions instead of arbitrary client-side writes.
5. Give LLMs only the variables, object types, searches, functions, applications, and actions required by the current workflow.
6. Distinguish read access from write access and keep consequential actions reviewable and auditable.

## Brain and retrieval integration

`workers/ontology_workers.py` already loads every `workers/knowledge/*.jsonl` file, so the engineering knowledge pack is automatically visible to ontology retrieval and the agent daemon's relevant-knowledge injection. All maintained GPT/XUNIA Modelfiles are also instructed to apply this stack when planning engineering work.

The source guide URLs are provenance references, not a claim that GPT-DOUG is Palantir Foundry or connected to a Palantir tenant.
