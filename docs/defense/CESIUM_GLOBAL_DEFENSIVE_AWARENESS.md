# CESIUM-ITAK: Global Defensive Situational Awareness

Status: proposed reference architecture; not deployed.

## Mission

Build a geospatial common-operating-picture application for authorized defensive monitoring, hazard awareness, incident coordination, and resilience planning. Use CesiumJS for a 3D globe and interoperable geospatial layers. Treat iTAK/TAK-style interoperability as an optional, separately reviewed integration rather than assuming access to any external network.

This project is not a weapon, targeting system, electronic-attack tool, cyberattack platform, or automated engagement system. It must not issue commands to effectors or generate target engagement recommendations.

## Initial release scope

1. **3D geospatial view** — globe, terrain/imagery layers, user-approved operational overlays, map legend, layer provenance, and data freshness.
2. **Defensive event intake** — typed incident, hazard, infrastructure-status, and sensor-health events from explicitly authorized feeds.
3. **Event triage** — deduplication, confidence labels, timestamps, source quality, geospatial uncertainty, and analyst annotations.
4. **Common operating picture** — filters by time, region, event category, severity, and verification state.
5. **Coordination** — human-authored incident notes, task ownership, acknowledgement, escalation, and status tracking.
6. **Resilience simulation** — tabletop exercises and synthetic events to test response procedures without connecting to operational effectors.
7. **Audit and export** — role-gated reports with source lineage, access logging, redaction, and export controls.

## Explicit exclusions

- No weapon construction, command-and-control for weapons, automated target selection, fire-control, or engagement workflows.
- No jamming, spoofing, directed-energy, malware, exploit delivery, or other interference against third-party systems.
- No autonomous action against people, vehicles, networks, or infrastructure.
- No ingestion of classified, sensitive, or personal data without an approved environment, authorization, retention policy, and access controls.
- No assumption that public data is accurate, safe to act on, or licensed for unrestricted reuse.

## Reference architecture

```text
Authorized sources / synthetic exercise generator
                 |
                 v
      Ingestion adapters + schema validation
                 |
                 v
    Normalization / deduplication / provenance
                 |
                 v
   Policy gate + access control + audit events
                 |
                 v
  Event store / geospatial query / freshness checks
                 |
                 v
 CesiumJS globe + incident queue + analyst workflow
                 |
                 v
 Human-approved reports / defensive coordination
```

Each adapter is read-only by default. Write operations are limited to internal annotations and workflow state. Any external side effect requires a separately authorized integration, explicit policy, human approval, and audit record.

## Event contract

Every event should include a stable event ID, schema version, category, observation time, ingestion time, source identity, provenance reference, confidence, verification status, location and uncertainty when available, severity rationale, data classification, and retention policy. Unknown or missing values must remain unknown rather than being inferred.

Use WGS84 longitude/latitude for geographic coordinates and explicitly record coordinate reference systems for other spatial data. Preserve source timestamps and timezone offsets. Validate coordinate ranges, payload sizes, event rate, and allowed categories.

## Security model

- Authenticate every user and service; use least privilege and role-based access.
- Enforce tenant, organization, and data-classification boundaries on the server, not only in the UI.
- Allowlist source endpoints and outbound destinations; deny unapproved egress.
- Keep secrets out of source control, prompts, logs, and browser bundles.
- Treat source content as untrusted; validate and normalize before display or downstream processing.
- Log access, changes, exports, approvals, policy decisions, and data-source health; redact sensitive values.
- Fail closed on missing identity, policy, provenance, or authorization checks.
- Provide rate limits, bounded retries, timeouts, cancellation, backups, and tested recovery.
- Use synthetic data in development and demonstrations.

## Human factors and safe operation

Display source, age, confidence, verification, and uncertainty together. Do not render a single confidence score as certainty. Mark stale feeds and outages visibly. Separate observations from analyst assessments and model-generated hypotheses. Every AI-generated summary must link to its supporting events and remain advisory.

## Delivery stages

### Stage 1 — Contracts and threat model
- Approve data classification, user roles, event schema, retention, threat model, and deployment boundary.
- Create synthetic fixtures and schema-validation tests.

### Stage 2 — Read-only Cesium prototype
- Build a CesiumJS globe with synthetic incidents, layer toggles, time filters, event details, and freshness indicators.
- No external feeds or operational integrations by default.

### Stage 3 — Backend and governed ingestion
- Add authenticated API, validated adapters, event persistence, geospatial/time queries, deduplication, and source health.
- Test malformed input, stale data, duplicates, unauthorized requests, and rate-limit behavior.

### Stage 4 — Analyst workflow
- Add notes, ownership, acknowledgement, incident status, export permissions, and audit history.
- Require human review for escalations and reports with consequential implications.

### Stage 5 — Simulation and resilience
- Add synthetic scenario playback, outage injection, and tabletop metrics.
- Ensure simulations cannot transmit commands to external systems.

### Stage 6 — Independent verification and controlled release
- Run unit/integration/security tests, dependency scans, access-control tests, recovery drills, and usability review.
- Require documented owner approval before production deployment or connection to any real operational feed.

## Acceptance criteria

- Schema and API validation reject invalid or unauthorized data.
- UI clearly shows event provenance, age, uncertainty, and verification state.
- No control or API path exists for targeting, engagement, jamming, spoofing, or destructive external actions.
- All exports and consequential workflow changes are permission-checked and audited.
- Synthetic demo works without credentials or live external feeds.
- Recovery, retention, access revocation, and incident response are documented.

## Current status

This document is an implementation blueprint only. It does not mean Cesium, iTAK, live sensor feeds, or a deployed global defense network have been installed or connected.