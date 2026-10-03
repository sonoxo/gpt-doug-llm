# GPT-DOUG INTEL BRIEF // USPTO PALANTIR-QUERY TECHNOLOGY LANDSCAPE

**Date:** 2026-09-12  
**Authority:** United States Patent and Trademark Office (USPTO) Patent Public Search plus user-supplied U.S. patent/publication front pages  
**Source query:** `palantir`  
**Reported search results:** `3544`; supplied search captures cover pages `1 of 71` and `2 of 71`  
**Exact document-front-page records:** `13`  
**Disposition:** `KEEP_AS_PUBLIC_PRIOR_ART_AND_ARCHITECTURE_WATCHLIST`

## Evidence model

GPT-DOUG keeps keyword-search records separate from exact supplied patent/publication front pages. Search presence alone does not establish applicant, assignee, ownership, validity, enforceability, infringement, or freedom to operate. Exact front pages can support document-level Applicant/Assignee attribution when those fields are visibly printed, but they still do not establish current assignment status or legal clearance.

Architecture mappings are engineering inferences and independent-design review triggers, not claim interpretations or implementation specifications.

## Exact Palantir-attributed document set

| Document | Date | Front-page attribution | Architecture watch |
| --- | --- | --- | --- |
| `US-20260119865-A1` | 2026-04-30 | Applicant | eligibility engine + GAI criteria evaluation |
| `US-20260093834-A1` | 2026-04-02 | Applicant | shared-infrastructure data security/compliance/governance |
| `US-12591555-B2` | 2026-03-31 | Applicant + Assignee | live data migration + consistency/resilience |
| `US-12585804-B2` | 2026-03-24 | Applicant + Assignee | object/attribute permission governance |
| `US-20260080157-A1` | 2026-03-19 | Applicant | GAI evidence-routed document workflow |
| `US-12579156-B2` | 2026-03-17 | Applicant + Assignee | linked-dataset interactive visualization |
| `US-12572542-B2` | 2026-03-10 | Applicant + Assignee | natural-language-to-data-pipeline generation |
| `US-12572545-B2` | 2026-03-10 | Applicant + Assignee | ontology query execution planning |
| `US-20260017391-A1` | 2026-01-15 | Applicant | data-platform security enforcement |
| `US-20260017828-A1` | 2026-01-15 | Applicant | branch-aware dataset synchronization |
| `US-20260017267-A1` | 2026-01-15 | Applicant | recursive resource discovery + governed deletion |
| `US-20260019665-A1` | 2026-01-15 | Applicant | access-controlled secure communications orchestration |
| `US-12487876-B2` | 2025-12-02 | Applicant + Assignee | language-model-assisted error analysis |

All 13 supplied front pages identify **Palantir Technologies Inc.** in an Applicant field, and the issued patents in this set additionally show an Assignee field where captured. These are document-level attributions only.

## Newly added architecture-watch patterns

### Natural-language data-pipeline generation — `US-12572542-B2`
Visible flow: NL query + datasets → model-query generation → model selection/result → dataset transformation → data-pipeline generation → optional pipeline display.

GPT-DOUG watch mapping: natural-language workflow intake, ontology-aware query planning, governed model selection, pipeline generation, visualization and audit.

### Ontology query execution planning — `US-12572545-B2`
Visible/public front-page material supports a watch around ontology queries, database-query transformation, join planning, execution plans and controlled execution.

GPT-DOUG mapping: ontology query planner, federated data access, cost-aware planning, query-plan auditability and governed ontology runtime.

### Data-platform security enforcement — `US-20260017391-A1`
Visible components include a process engine, definition engine, enforcement engine, networked computing devices and storage.

GPT-DOUG mapping: Glass Onion policy definitions, classification-aware access rules, policy enforcement, authorization audit and human review for consequential policy changes.

### Dataset synchronization — `US-20260017828-A1`
Visible architecture includes a data-processing platform, application servers, client device, network, network-based permissioning system and resource database.

GPT-DOUG mapping: branch-aware dataset synchronization, permission-gated updates, replication consistency checks, merge verification and change audit.

### Recursive resource discovery and deletion — `US-20260017267-A1`
Visible process-engine components include node, dependence, deletion and recursion engines connected to data stores.

GPT-DOUG mapping: ontology dependency graphs, recursive discovery, retention-policy evaluation, dependency-aware deletion planning, explicit human approval and deletion audit. Destructive actions remain separately authorized.

### Secure communications orchestration — `US-20260019665-A1`
Visible/public material supports a watch around initiating an audio/video channel, reading an access-control attribute and instantiating the channel according to policy.

GPT-DOUG mapping: secure communications requests, identity/access validation, classification-aware policy gates, approved participants and auditable channel creation. This watch is expressly limited to secure communications/access control and does not authorize targeting, weapons control or autonomous operational command.

### Language-model-assisted error analysis — `US-12487876-B2`
Visible diagram shows error-message input, context generation from documents/code/error context/other information, prompt generation, LLM analysis and an explanation/suggested fix.

GPT-DOUG mapping: diagnostic event intake, context assembly, prompt construction, LLM-assisted root-cause analysis, remediation recommendation and human verification before any changes.

## Existing architecture-watch set

Earlier exact records remain active for eligibility engines, shared-infrastructure access governance, live migration, GAI document workflows and linked-dataset visualization. The broader two-page search landscape also retains ontology automation/query, software supply chain, network anomaly detection, audit/action logging, geospatial interfaces, identity federation, access control, monitoring/alerting and distributed-system design as research-watch themes.

## Independent-design rule

When GPT-DOUG encounters overlap with one of these areas it should preserve source provenance, distinguish document fact from engineering inference, retain independent requirements/design notes/commits/tests, prefer standards and documented public APIs, trigger human review before claim-level or freedom-to-operate conclusions, and never clone a claimed implementation from patent language or diagrams.

## Runtime commands

```bash
zyrapalantir patent-intel summary
zyrapalantir patent-intel attributed
zyrapalantir patent-intel eligibility-engine
zyrapalantir patent-intel search pipeline
zyrapalantir patent-intel search ontology
zyrapalantir patent-intel search security
zyrapalantir patent-intel search synchronization
zyrapalantir patent-intel search deletion
zyrapalantir patent-intel search communications
zyrapalantir patent-intel search error-analysis
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

The exact front pages materially improve source quality by visibly identifying Palantir Technologies Inc. as Applicant and, for captured issued patents, Assignee. For GPT-DOUG, the engineering value is a provenance-aware architecture watch spanning ontology execution, NL-to-pipeline generation, governed access, synchronization, retention/deletion, secure communications, diagnostics, migration, document workflows and visualization. The correct use remains **research awareness, independent design and review gating**, not legal clearance.
