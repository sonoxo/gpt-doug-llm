# GoDsEye Continuous Monitoring and Threat-Awareness Ontology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add continuous allowlisted public-source monitoring, deduplicated provenance records, neutral threat-awareness ontology objects, and non-operational live status events to GoDsEye.

**Architecture:** Reuse existing global-intel, global-compliance, and BioFusion source functions as authoritative adapters. Persist only normalized observation metadata in a local append-safe state directory, add a separate neutral threat-awareness ontology instead of target objects, and let FastAPI lifespan own an optional monitor loop that emits public status/freshness events only.

**Tech Stack:** Python 3.9+, pathlib/json/hashlib/asyncio, existing FastAPI lifespan and EventHub, pytest, JSON ontology files.

**Spec:** docs/superpowers/specs/2026-10-07-gpt-doug-planetary-godseye-design.md

## Global Constraints

- Poll only allowlisted official/public sources already approved by the relevant adapters.
- Source fitness is not geopolitical threat severity.
- Never label a person or organization as an adversary without explicit authoritative-source evidence.
- Never convert awareness data into targeting, engagement, hack-back, implant-control, or destructive instructions.
- Tier 4/community sources are never authoritative alone.
- Monitoring must be optional, stoppable, and safe when every source is offline.
- Live events are status/freshness notifications only and stay within PUBLIC, TRAINING, or SIMULATION classes.

## Review Focus

- Duplicate observations must deduplicate by canonical digest and advance last-seen metadata.
- A Tier 4 source conflicting with Tier 1 must produce EvidenceConflict and preserve Tier 1 authority.
- All sources offline must yield a safe OFFLINE cycle and normal sleep/backoff.
- Corrupt state must be quarantined, not deleted.
- App shutdown must cancel the monitor promptly.

---

### Task 1: Observation record model and deduplicating store

**Files:**
- Create: godseye/monitoring.py
- Test: tests/test_godseye_monitoring.py

**Interfaces:**
- Produces ObservationRecord(id, source_id, tier, observed_at, first_seen_at, last_seen_at, provenance, digest, payload)
- Produces ObservationStore(state_dir: str | Path | None = None)
- Produces ObservationStore.upsert(source_id: str, tier: int, provenance: str, payload: dict, observed_at: str) -> ObservationRecord
- Produces ObservationStore.list(limit: int = 200) -> list[ObservationRecord]
- Produces ObservationStore.status() -> dict

- [ ] Step 1: Write a failing deduplication test: upsert the same canonical payload twice with different observed_at values; require one record, stable first_seen_at, and advanced last_seen_at.
- [ ] Step 2: Run pytest tests/test_godseye_monitoring.py::test_store_deduplicates_by_canonical_digest -v; expected FAIL.
- [ ] Step 3: Implement canonical sorted-JSON hashing and atomic state writes using temp file plus os.replace.
- [ ] Step 4: Write a failing corrupt-state test requiring invalid JSON to be renamed to a .corrupt-* file while a new empty state is created with a recovery warning.
- [ ] Step 5: Run the corrupt-state test; expected FAIL.
- [ ] Step 6: Implement quarantine recovery without deleting the unreadable evidence file.
- [ ] Step 7: Run pytest tests/test_godseye_monitoring.py -v; expected PASS.
- [ ] Step 8: Commit the store and tests.

### Task 2: Source tiers and neutral threat-awareness ontology

**Files:**
- Create: safety-shield/ontology/godseye-threat-awareness-v1.json
- Create: godseye/ontology.py
- Test: tests/test_godseye_threat_ontology.py

**Interfaces:**
- Object types: ThreatActorReference, ThreatCampaignReference, AdvisoryReference, VulnerabilityReference, SanctionsOrDesignationReference, SourceAssessment, ConfidenceAssessment, ComplianceImpact, GeographicScope, SectorScope, EvidenceConflict.
- Relationships: SUPPORTED_BY, CONTRADICTED_BY, AFFECTS_SECTOR, AFFECTS_REGION, RELEVANT_TO_COMPLIANCE, REFERENCES_VULNERABILITY, ATTRIBUTED_BY_SOURCE.
- Produces load_threat_ontology(path: str | Path | None = None) -> dict
- Produces source_tier(source_id: str, source_meta: dict) -> int
- Produces evidence_conflict(primary: ObservationRecord, secondary: ObservationRecord) -> dict

- [ ] Step 1: Write failing schema tests requiring every object/relationship, target_objects_allowed false, and authority EVIDENCE_REFERENCE_ONLY.
- [ ] Step 2: Run pytest tests/test_godseye_threat_ontology.py::test_threat_ontology_is_reference_only -v; expected FAIL.
- [ ] Step 3: Create the ontology JSON and loader.
- [ ] Step 4: Write failing deterministic tier tests: official government/CERT Tier 1, standards/regulatory Tier 2, explicitly configured research/vendor/news Tier 3, unknown/community Tier 4.
- [ ] Step 5: Run the tier test; expected FAIL.
- [ ] Step 6: Implement explicit registry-based tiering; do not infer authority merely from domain-name resemblance.
- [ ] Step 7: Add a failing conflict test requiring both evidence references to survive while lower numeric tier is marked higher authority.
- [ ] Step 8: Implement evidence_conflict and run pytest tests/test_godseye_threat_ontology.py -v; expected PASS.
- [ ] Step 9: Commit ontology, loader, and tests.

### Task 3: One-shot allowlisted poll cycle

**Files:**
- Modify: godseye/monitoring.py
- Test: tests/test_godseye_monitoring.py

**Interfaces:**
- Consumes global_intel_benchmark(force=True), global_catalog(), global_posture(settings), bioinformatics_fusion(force=True), source_tier, and ObservationStore.upsert.
- Produces poll_once(*, store: ObservationStore, settings, intel_fn=global_intel_benchmark, compliance_catalog_fn=global_catalog, compliance_posture_fn=global_posture, bio_fn=bioinformatics_fusion, now_fn=None) -> dict
- Return schema gpt-doug.godseye-monitor-cycle.v1 with ONLINE, DEGRADED, or OFFLINE; source counts; new/updated record counts; errors; provenance.

- [ ] Step 1: Write a failing all-online test with fake adapters; require source IDs, tiers, provenance, and no target objects.
- [ ] Step 2: Run pytest tests/test_godseye_monitoring.py::test_poll_once_normalizes_allowlisted_sources -v; expected FAIL.
- [ ] Step 3: Implement normalization only from existing allowlisted adapter outputs; add no arbitrary URL fetcher.
- [ ] Step 4: Write a failing all-offline test where every adapter raises TimeoutError; require OFFLINE, errors for each adapter, and zero fake successes.
- [ ] Step 5: Run the offline test; expected FAIL.
- [ ] Step 6: Implement per-adapter isolation and cycle status aggregation.
- [ ] Step 7: Run pytest tests/test_godseye_monitoring.py -v; expected PASS.
- [ ] Step 8: Commit poll-cycle changes.

### Task 4: Optional continuous monitor service and public status events

**Files:**
- Create: godseye/service.py
- Modify: agency_cloud/app.py
- Test: tests/test_godseye_service.py
- Test: agency_cloud/tests/test_godseye_monitor_api.py

**Interfaces:**
- Consumes poll_once and agency_cloud.realtime.event_hub.broadcast.
- Produces GoDsEyeMonitor(store, settings, interval_seconds: float = 300.0, poll_fn=poll_once, broadcaster=event_hub.broadcast)
- Produces async GoDsEyeMonitor.run() -> None
- Produces GoDsEyeMonitor.stop() -> None
- Produces GoDsEyeMonitor.status() -> dict
- Add GET /api/v1/godseye/monitor/status
- Environment GODSEYE_MONITOR_ENABLED default 0
- Environment GODSEYE_MONITOR_INTERVAL_SECONDS default 300

- [ ] Step 1: Write a failing event test requiring one cycle to broadcast event type GODSEYE_SOURCE_STATUS with classification PUBLIC and no operational-control fields.
- [ ] Step 2: Run pytest tests/test_godseye_service.py::test_monitor_broadcasts_public_status_only -v; expected FAIL.
- [ ] Step 3: Implement GoDsEyeMonitor with an event-based interruptible wait between cycles.
- [ ] Step 4: Write failing cancellation and all-offline loop tests requiring prompt shutdown and no rapid spin.
- [ ] Step 5: Run pytest tests/test_godseye_service.py -k "cancel or offline" -v; expected FAIL.
- [ ] Step 6: Integrate monitor creation/start/stop into agency_cloud.app.lifespan only when GODSEYE_MONITOR_ENABLED=1; disabled behavior must remain unchanged.
- [ ] Step 7: Add a failing monitor-status route test covering both enabled and disabled states.
- [ ] Step 8: Implement the status route and run pytest tests/test_godseye_service.py agency_cloud/tests/test_godseye_monitor_api.py -v; expected PASS.
- [ ] Step 9: Commit service, lifecycle, route, and tests.

### Task 5: Monitoring and ontology regression gate

**Files:** no new files unless a touched-file regression is found.

- [ ] Step 1: Run:

    pytest tests/test_godseye_monitoring.py tests/test_godseye_threat_ontology.py tests/test_godseye_service.py agency_cloud/tests/test_godseye_monitor_api.py agency_cloud/tests/test_godseye_api.py agency_cloud/tests/test_service.py -v

Expected: PASS.

- [ ] Step 2: Run:

    python3 -m json.tool safety-shield/ontology/godseye-threat-awareness-v1.json >/dev/null
    python3 -m compileall godseye agency_cloud

Expected: exit 0.

- [ ] Step 3: Commit only if a regression correction was necessary.
