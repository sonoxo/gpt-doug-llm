# THE BLACK HOUSE // INTELLIGENCE PR COLLABORATION STANDARD

## Purpose

This is the review contract for research-driven pull requests affecting GPT-DOUG-LLM, RVIA, ZYRA, XUNIA, EYERIS, SHADOW GLASS, GLASS ONION, or The Black House.

The objective is to move quickly **without turning interesting source material into unverified system truth**.

## Required PR sections

Every intelligence/research PR should contain:

### 1. Mission
What operational question or architecture decision does the research inform?

### 2. Primary sources
List original URLs. Identify each as:
- `FIRST_PARTY`
- `CREDIBLE_ASSOCIATED`
- `SECONDARY`
- `LEAD_ONLY`

### 3. Extracted claims
For each claim provide:
- claim text in our own words;
- source;
- source tier;
- confidence;
- corroboration;
- unresolved gap.

### 4. Implementation delta
State exactly what code, ontology, policy, agent knowledge, workflow, docs, or evals are changing because of the research.

### 5. Security/data boundary
Confirm:
- no secrets or credentials;
- no unlawfully obtained material;
- no classified or restricted information was assumed authorized;
- external-model egress remains policy-gated;
- consequential actions remain bounded and human-accountable where required.

### 6. Evaluation evidence
Include the tests/evals used to prove the implementation did not regress:
- schema validation;
- unit/integration tests;
- provenance checks;
- grounding/citation evals;
- negative data-egress/security tests when relevant;
- rollback test for consequential workflows.

### 7. Confidence statement
Use only:
- `VERY HIGH` — current first-party documentation directly supports the claim;
- `HIGH` — strong associated evidence plus first-party corroboration;
- `MEDIUM` — credible but incompletely corroborated;
- `LOW` — research lead only.

### 8. Independence / attribution
Research using Palantir material must state:

> This project is independent and open source. References to Palantir Technologies, its products, employees, documentation, or public materials are for research, interoperability, and attribution only and do not imply endorsement, affiliation, certification, contract, or access to proprietary systems.

## Merge gate

A research PR is eligible to merge when:

```text
SOURCE PRESENT
   +
PROVENANCE RECORDED
   +
CLAIM / FACT / INFERENCE SEPARATED
   +
CONFIDENCE SCORED
   +
PRIMARY DOCS LINKED WHERE AVAILABLE
   +
IMPLEMENTATION TESTED
   +
SECURITY / AUTHORITY BOUNDARY PRESERVED
   =
PR-READY
```

## Current exemplar

The Palantir institutional-sovereignty dossier is the reference implementation for this standard:

- [`briefings/2026-09-02-palantir-basis-points-institutional-sovereignty.md`](./briefings/2026-09-02-palantir-basis-points-institutional-sovereignty.md)
- [`sources/youtube-egr-UDWLZPI.json`](./sources/youtube-egr-UDWLZPI.json)
- [`PALANTIR_RESEARCH_CREDITS.md`](./PALANTIR_RESEARCH_CREDITS.md)
