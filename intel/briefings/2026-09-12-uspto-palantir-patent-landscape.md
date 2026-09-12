# GPT-DOUG INTEL BRIEF // USPTO PALANTIR-QUERY TECHNOLOGY LANDSCAPE

**Date:** 2026-09-12  
**Authority:** United States Patent and Trademark Office (USPTO) Patent Public Search plus user-supplied U.S. patent/publication front pages  
**Source query:** `palantir`  
**Reported search results:** `3544`; supplied search captures cover pages `1 of 71` and `2 of 71`  
**Exact document-front-page records:** `6`  
**Disposition:** `KEEP_AS_PUBLIC_PRIOR_ART_AND_ARCHITECTURE_WATCHLIST`

## Evidence model

GPT-DOUG keeps two evidence classes separate:

1. **Keyword-search records** — useful for public prior-art and architecture-watch discovery, but search presence alone does not establish applicant, assignee, current ownership, validity, enforceability, infringement, or freedom to operate.
2. **Exact supplied front pages** — the visible Applicant and, when present, Assignee fields support document-level party attribution with `HIGH_FROM_DOCUMENT_FRONT_PAGE` confidence. They still do not establish current assignment status, legal validity, enforceability, infringement, or freedom to operate.

Architecture mappings below are engineering inferences used as independent-design review triggers. They are not claim interpretations or implementation specifications.

## Exact Palantir-attributed document set

| Document | Date | Front-page attribution | Architecture watch |
| --- | --- | --- | --- |
| `US-20260119865-A1` | 2026-04-30 | Applicant: Palantir Technologies Inc. | eligibility engine + GAI criteria evaluation |
| `US-20260093834-A1` | 2026-04-02 | Applicant: Palantir Technologies Inc. | shared-infrastructure data security/compliance/governance |
| `US-12591555-B2` | 2026-03-31 | Applicant + Assignee: Palantir Technologies Inc. | live data migration + consistency/resilience |
| `US-12585804-B2` | 2026-03-24 | Applicant + Assignee: Palantir Technologies Inc. | object/attribute permission governance in shared infrastructure |
| `US-20260080157-A1` | 2026-03-19 | Applicant: Palantir Technologies Inc. | GAI evidence-routed document workflow |
| `US-12579156-B2` | 2026-03-17 | Applicant + Assignee: Palantir Technologies Inc. | linked-dataset interactive visualization |

## Architecture-watch patterns added to GPT-DOUG

### Eligibility engine / GAI criteria evaluation

`US-20260119865-A1` visibly presents a flow containing Trigger, Eligibility Evaluation, Criterion Evaluation, GAI Logic, Add/Update, Dispatcher Function and Evaluation Function Set.

GPT-DOUG maps this only at a high level to ontology object eligibility, governed criteria evaluation, AI-assisted policy evaluation, state transitions, dispatcher/orchestration and human-review gates for consequential decisions.

### Shared-infrastructure security, compliance and governance

`US-20260093834-A1` and `US-12585804-B2` strengthen the architecture watch around clients, shared data systems, data objects/structures, access permissions, object/attribute permissions and governed request evaluation.

GPT-DOUG maps this to Glass Onion policy gates, ontology object/property permissions, least privilege, authorization audit and human review for consequential access decisions.

### Live data migration

`US-12591555-B2` adds a watch around live migration between source and destination data systems while maintaining operational continuity.

GPT-DOUG maps this to migration planning, replication/synchronization, rollback-aware operations, continuity monitoring and migration-state audit. The implementation must remain independently designed.

### Generative-AI document workflow

`US-20260080157-A1` visibly shows an external system, data connector, documentation triggers, requirements/criteria, evidence extraction, document-type determination, route selection, document generation, user-facing workflow, feedback and user-action tracking.

GPT-DOUG maps this to governed evidence ingestion, ontology-based document classification, policy-controlled routing, AI-assisted drafting, human review, feedback and audit trails.

### Linked-dataset visualization

`US-12579156-B2` adds a watch around datasets, linked objects/attributes, correlated rows, graphical indicators and interactive chart presentation.

GPT-DOUG maps this to the ZYRAPALANTIR visual control map, ontology-linked datasets, readiness views, correlated audit visualization and human-readable operational summaries.

## Broader search-landscape themes

The two captured search-result pages also retain architecture-watch signals around ontology automation/query, federated ontology databases, AI workflow governance, secure software deployment, artifact transport, network anomaly detection, audit/action logging, geospatial interfaces, identity federation, granular access control, data harmonization, monitoring/alerting, distributed computing and model-assisted diagnostics.

## Independent-design rule

When GPT-DOUG encounters overlap with one of these areas it should:

- preserve the source document number and evidence type;
- distinguish front-page fact from architecture inference;
- retain independent requirements, design notes, commits and test history;
- prefer standards and documented public APIs;
- trigger human review before claim-level analysis or freedom-to-operate conclusions;
- never clone a claimed implementation from patent language or diagrams.

## Runtime commands

```bash
zyrapalantir patent-intel summary
zyrapalantir patent-intel attributed
zyrapalantir patent-intel eligibility-engine
zyrapalantir patent-intel search governance
zyrapalantir patent-intel search migration
zyrapalantir patent-intel search document-generation
zyrapalantir patent-intel search visualization
zyrapalantir patent-intel themes
zyrapalantir patent-intel doctor
```

## Implementation

- search page 1: `intel/sources/uspto-palantir-query-2026-09-12.json`
- search page 2: `intel/sources/uspto-palantir-query-2026-09-12-page2.json`
- exact sources: `intel/sources/uspto-palantir-attributed-*.json`
- aggregate CLI: `scripts/zyrapalantir_patent_intel.py`
- ontology: `safety-shield/agents/knowledge/gpt-doug-uspto-patent-intel-v1.json`
- validation: `tests/test_zyrapalantir_patent_intel.py`

## Intelligence judgment

The exact front pages materially improve source quality because they visibly identify Palantir Technologies Inc. as Applicant and, on several issued patents, Assignee. For GPT-DOUG, the engineering value is a stronger provenance-aware architecture watch across governed eligibility, access control, live migration, AI document workflows and interactive visualization. The correct use remains **research awareness, independent design and review gating**, not legal clearance.
