# ZYRA / XUNIA Mission Support Workbench

Status: analyst decision-support scaffold.

## Purpose
Provide a Maven-inspired operational picture for authorized defensive analysis without implementing external actuation or engagement logic.

## Core workflow

```text
AUTHORIZED SOURCES
      |
      v
PROVENANCE + NORMALIZATION
      |
      v
EVIDENCE / INCIDENT CORRELATION
      |
      v
CONFIDENCE + QUALITY SCORING
      |
      v
ANALYST REVIEW QUEUE
      |
      v
HUMAN DECISION + AUDIT RECORD
```

## Workbench modules

- Source registry: source identity, authority, freshness, checksum and lineage.
- Evidence inbox: normalized evidence records with timestamp and confidence.
- Incident graph: links incidents, systems, assets, findings, sources and evidence.
- Review queue: prioritizes incomplete, conflicting or high-severity cases for analysts.
- Timeline replay: reconstructs what was known at a specific point in time.
- Geospatial context: optional defensive map layers and safety-zone overlays.
- Decision packet: packages evidence, uncertainty and provenance for human review.
- Audit ledger: records who reviewed what, when, and which evidence supported the decision.

## Control boundary

The workbench is read-only decision support by default. Material external actions are outside this scaffold and require a separately authorized system boundary. Unknown actions fail closed.

## Maven / Foundry mapping

Object types:

- Mission
- Source
- Evidence
- Incident
- Asset
- Finding
- Assessment
- DecisionPacket
- ReviewEvent
- AuditRecord

Relationships:

- DERIVED_FROM
- INFORMS
- AFFECTS
- ASSESSED_BY
- REVIEWED_BY
- RECORDED_IN
- SUPPORTED_BY

## Next engineering steps

1. Add schema validation for evidence and incident records.
2. Add deterministic confidence/quality aggregation.
3. Add review-queue API and audit events.
4. Add XUNIA map/timeline visualization.
5. Add Maven/Foundry ontology adapters.
6. Add synthetic scenario fixtures and replay tests.
7. Keep all material external actions fail-closed and human-controlled.
