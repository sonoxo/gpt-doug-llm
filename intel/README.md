# 🏛️ THE BLACK HOUSE // INTELLIGENCE INDEX

This directory stores **source-traceable intelligence artifacts** for ZYRA, XUNIA, GPT-DOUG-LLM, VIRGINIA-LLM, and RVIA.

## Operating rule

```text
SOURCE CLAIM ≠ VERIFIED FACT
MODEL OUTPUT ≠ AUTHORITY
```

Every intelligence item should preserve:

- source URL and retrieval context;
- provenance and framing notes;
- transcript/extraction status;
- independently verified facts;
- analyst assessment;
- confidence and gaps;
- disposition (`KEEP`, `REVIEW`, `QUARANTINE`, `REJECT`);
- links to ontology/workflow implications.

## Current briefs

| Date | Source | Topic | State | Brief |
| --- | --- | --- | --- | --- |
| 2026-09-02 | YouTube Short `uFFFRTrSosc` | What Palantir does / AIP architecture | `AMBER` | [`Open brief`](./briefings/2026-09-02-youtube-uFFFRTrSosc-palantir.md) |

## Machine-readable sources

- [`youtube-uFFFRTrSosc.json`](./sources/youtube-uFFFRTrSosc.json)

## Agentic control plane

- [`AIP Agentic Workflows`](../safety-shield/AIP_AGENTIC_WORKFLOWS.md)
- [`External model egress policy`](../safety-shield/policies/external-model-egress.rego)
- [`External model registry`](../safety-shield/model-registry/external-model-registry.schema.json)
- [`SHADOW GLASS`](../safety-shield/SHADOW_GLASS.md)
- [`Safety Shield`](../safety-shield/README.md)

## Source lifecycle

```text
DISCOVER
  ↓
CAPTURE SOURCE RECORD
  ↓
TRANSCRIPT / EXTRACT WHEN AVAILABLE
  ↓
SEPARATE CLAIM FROM FRAMING
  ↓
CORROBORATE
  ↓
SCORE CONFIDENCE
  ↓
MAP INTO ONTOLOGY
  ↓
RUN AGENTIC WORKFLOW / EVALS
  ↓
PUBLISH BLACK HOUSE BRIEF
  ↓
AUDIT + RETAIN GAPS
```
