# GPT-Doug Planetary GoDsEye Design

Date: 2026-10-07  
Branch: `feature/us-01-godswarhawk`

## 1. Purpose

Build a unified GPT-Doug planetary intelligence and orchestration layer that connects the existing GPT-Doug Brain, WarHawk, ZYRA MSS, global intelligence, global compliance, BioFusion, XUNIA Planet/MMGIS, and platform UI into one coherent operator experience.

This design implements both:
1. an in-map GPT-Doug copilot for XUNIA Planet/MMGIS; and
2. a backend planetary orchestration API for read-only fusion, planning, analysis, simulation, provenance, and human-approved workflow handoff.

The system remains bounded to authorized/public data, defensive analysis, software engineering, compliance, readiness, research, and simulation. It does not provide private Pentagon access, autonomous targeting, weapons release, hostile engagement, hack-back, implant control, or unattended real-world actuation.

## 2. Success Criteria

The implementation is successful when:

- `gpt-doug godseye status` reports the fused state of WarHawk, ZYRA MSS, global intel, global compliance, BioFusion, platform health, and XUNIA Planet integration.
- `gpt-doug godseye query "<question>"` produces an ontology/provenance-backed read-only synthesis.
- `gpt-doug planetary status` reports XUNIA/MMGIS integration state and source freshness.
- `gpt-doug planetary plan "<mission>"` creates a bounded mission plan that can reference geospatial, orbital, compliance, evidence, and system-health objects.
- A GoDsEye dashboard displays source health, provenance, compliance posture, WarHawk/ZYRA status, BioFusion simulation state, platform health, and XUNIA planetary context.
- XUNIA Planet/MMGIS exposes an in-map GPT-Doug copilot panel that uses the same backend API as the dashboard.
- The CLI works without requiring a system-wide editable pip install; repo-local or virtual-environment execution is supported.
- All new behavior is covered by unit and integration tests.
- Existing safety boundaries remain enforced.

## 3. Existing Components Reused

The design composes existing components instead of duplicating them:

- `gpt_brain`: ontology-first reasoning and memory-backed orchestration.
- `warhawk`: bounded six-worker software/research swarm.
- `safety-shield/ontology/zyra-mss-v1.json`: mission-support ontology and 100-worker logical fleet.
- `agency_cloud/global_intel.py`: public-source strategic awareness and source-fitness benchmarking.
- `agency_cloud/global_compliance.py`: global compliance and regulatory posture.
- `agency_cloud/bioinformatics.py`: public scientific references plus synthetic biochip digital twin.
- `agency_cloud/app.py`: FastAPI surface, WebSocket events, platform routes.
- `agency_cloud/platform.py`: platform manifest, event policy, source registry.
- `eagleeye-cloud` and `agency_cloud/static`: existing operator dashboards.
- `docs/planet/index.html`: XUNIA Planet/MMGIS planetary surface.
- existing XUNIA/MMGIS orbital and geospatial integration points.

## 4. Architecture

### 4.1 GoDsEye Fusion Core

Create a new `godseye` package with focused modules:

- `godseye/models.py`
  - typed fusion snapshot objects
  - source state
  - compliance state
  - swarm state
  - biofusion state
  - planetary state
  - provenance references
  - uncertainty and freshness metadata

- `godseye/fusion.py`
  - reads existing subsystem status functions
  - never bypasses subsystem policy
  - produces a normalized read-only snapshot

- `godseye/query.py`
  - routes questions through GPT-Doug Brain using the fused snapshot as context
  - preserves provenance and uncertainty
  - blocks claims of external access/control unless evidence proves it

- `godseye/policy.py`
  - central read-only observation policy
  - mirrors WarHawk/ZYRA hard boundaries
  - denies weapon control, hostile engagement, hack-back, credential theft, implant control, destructive external action, and bypass of human authorization

- `godseye/planetary.py`
  - normalizes XUNIA/MMGIS planetary context
  - geographic objects
  - public orbital objects
  - infrastructure/readiness overlays
  - source freshness
  - simulation metadata

GoDsEye is an observer/fusion layer, not a new source of authority.

### 4.2 Planetary Orchestration API

Add API routes under `agency_cloud/app.py`:

- `GET /api/v1/godseye/status`
- `POST /api/v1/godseye/query`
- `GET /api/v1/godseye/sources`
- `GET /api/v1/planetary/status`
- `POST /api/v1/planetary/plan`
- `GET /api/v1/planetary/layers`

These routes call the new GoDsEye package and existing subsystem functions. They do not directly control devices, vehicles, implants, weapons, or external systems.

The existing WebSocket event stream may publish non-operational status/freshness events from GoDsEye.

### 4.3 In-Map XUNIA Copilot

Extend the XUNIA Planet/MMGIS surface with a dockable GPT-Doug panel.

The panel includes:

- Ask GPT-Doug
- Current map/viewport context
- Visible layers
- selected entity context
- source freshness
- provenance links
- compliance warnings
- WarHawk/ZYRA recommendation summaries
- mission-plan preview

The browser sends only explicit operator queries and visible authorized context to the backend. The backend returns analysis and recommendations. The panel does not execute arbitrary shell commands or real-world actions.

### 4.4 Unified GoDsEye Dashboard

Add `agency_cloud/static/godseye.html` and route `/godseye`.

Dashboard sections:

- System health
- GPT-Doug Brain readiness
- WarHawk worker state
- ZYRA MSS logical-fleet state
- Global-intel source health
- Compliance posture
- Evidence/provenance timeline
- XUNIA planetary layer status
- BioFusion digital-twin state
- Policy boundary status
- WebSocket live updates
- recent operator queries and mission plans

The dashboard is a read-only command-and-observation console. Existing focused dashboards remain available and are linked from GoDsEye.

## 5. CLI Design

Extend the real `gpt_brain.cli` command surface.

### GoDsEye

```text
gpt-doug godseye status
gpt-doug godseye query "show current source degradation and compliance risk"
gpt-doug godseye sources
```

### Planetary

```text
gpt-doug planetary status
gpt-doug planetary plan "compare visible planetary infrastructure dependencies"
gpt-doug planetary layers
```

### Existing

```text
gpt-doug warhawk status
gpt-doug warhawk plan "..."
gpt-doug warhawk run "..." --execute
gpt-doug status
gpt-doug doctor
```

A repo-local launcher will be added so the CLI does not depend on writing into externally managed Homebrew Python environments. The launcher will prefer:

1. project virtual environment if present;
2. repo-local Python module execution;
3. otherwise return a clear setup error.

## 6. Data Flow

```text
Public/Authorized Sources
        |
        +--> Global Intel
        +--> Global Compliance
        +--> Bioinformatics/BioFusion
        +--> XUNIA/MMGIS planetary/orbital context
        |
        v
Subsystem policy + provenance checks
        |
        v
GoDsEye Fusion Core
        |
        +--> GPT-Doug Brain query context
        +--> WarHawk bounded planning context
        +--> ZYRA MSS readiness/decision-support context
        |
        +--> FastAPI read-only routes
        +--> WebSocket status events
        |
        +--> GoDsEye dashboard
        +--> XUNIA in-map copilot
        +--> gpt-doug CLI
```

No path from GoDsEye directly performs real-world actuation.

## 7. Continuous Public-Source Monitoring

Continuous monitoring reuses and extends existing source-health mechanisms.

The monitoring layer:

- polls only allowlisted official/public sources;
- stores source metadata, freshness, status, and provenance;
- distinguishes source fitness from threat severity;
- deduplicates observations;
- emits status/freshness events;
- never labels a person or organization as an adversary without explicit authoritative-source evidence;
- never converts awareness data into targeting or engagement instructions.

Source tiers:

- Tier 1: official U.S./allied government and CERT/CSIRT sources
- Tier 2: recognized standards bodies and public regulatory sources
- Tier 3: reputable academic, security-vendor, and major-news sources
- Tier 4: community/secondary sources, clearly labeled and never treated as authoritative alone

## 8. Adversary/Threat Awareness Ontology

Extend ontology coverage with neutral evidence objects rather than target objects.

New object concepts:

- ThreatActorReference
- ThreatCampaignReference
- AdvisoryReference
- VulnerabilityReference
- SanctionsOrDesignationReference
- SourceAssessment
- ConfidenceAssessment
- ComplianceImpact
- GeographicScope
- SectorScope
- EvidenceConflict

Relationships include:

- SUPPORTED_BY
- CONTRADICTED_BY
- AFFECTS_SECTOR
- AFFECTS_REGION
- RELEVANT_TO_COMPLIANCE
- REFERENCES_VULNERABILITY
- ATTRIBUTED_BY_SOURCE

The ontology stores what sources say and with what confidence; it does not create autonomous target lists.

## 9. Safety and Policy

Existing hard boundaries remain mandatory:

BLOCK:
- autonomous target selection
- weapons release
- weapon/drone swarm control
- hostile engagement
- critical-infrastructure disruption
- hack-back
- credential theft
- unattended real-world vehicle control
- implant control
- destructive biological or cyber actuation
- bypassing human authorization

REVIEW:
- external messaging
- access-policy changes
- readiness-state changes
- software promotion
- real-world equipment actions

ALLOW:
- public/authorized ingestion
- ontology normalization
- provenance tracking
- defensive analysis
- compliance analysis
- read-only geospatial/orbital visualization
- simulation
- software planning
- recommendation generation
- test generation
- audit events

## 10. Error Handling

Each subsystem adapter returns:

- status: ONLINE / DEGRADED / OFFLINE
- last successful refresh
- source count
- errors
- stale flag
- provenance
- partial-data indicator

GoDsEye never fails the whole snapshot because one source is degraded. Instead it returns a partial snapshot with explicit uncertainty.

Query requests fail closed when:
- required context is malformed;
- policy blocks the request;
- provenance cannot be established for a claimed external capability.

## 11. Testing

### Unit tests

- GoDsEye snapshot normalization
- source-health degradation
- provenance preservation
- policy blocking
- partial snapshot behavior
- planetary context normalization
- CLI parser coverage
- query context composition
- no false claims of real external access

### API tests

- status route
- query route
- planetary routes
- invalid input handling
- policy-denied request handling
- WebSocket status event publication

### UI tests

- dashboard loads
- degraded subsystems render correctly
- provenance links display
- copilot request/response lifecycle
- no hidden real-world control actions

### Regression tests

- existing WarHawk CLI
- existing global-intel endpoints
- existing compliance endpoints
- existing BioFusion endpoints
- existing platform manifest
- existing blocked operational event types

## 12. Implementation Order

Phase 1: GoDsEye package and tests  
Phase 2: FastAPI routes and integration tests  
Phase 3: CLI integration and repo-local launcher  
Phase 4: GoDsEye dashboard  
Phase 5: XUNIA Planet/MMGIS copilot panel  
Phase 6: continuous monitoring and ontology extensions  
Phase 7: end-to-end verification and documentation

Each phase must keep the repository in a testable state.

## 13. Non-Goals

This project does not:

- create or claim access to private Pentagon/DoD systems;
- control weapons, drones, vehicles, implants, or critical infrastructure;
- perform offensive cyber operations;
- perform clinical or biological actuation;
- replace human authorization for governed actions;
- claim government endorsement or designation for project codenames.

## 14. Final Operator Experience

The intended operator experience is:

```text
gpt-doug status
gpt-doug godseye status
gpt-doug planetary status
gpt-doug warhawk status
```

The GoDsEye dashboard becomes the unified advanced console, while Eagle Eye and the other focused dashboards remain available as specialized views.

XUNIA Planet/MMGIS gains the same GPT-Doug copilot backed by the same GoDsEye fusion API, so terminal, dashboard, and map share one source of truth.
