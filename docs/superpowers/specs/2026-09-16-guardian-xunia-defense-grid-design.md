# GUARDIAN / XUNIA Defense Grid Design

## Status

Approved architecture for a defensive, human-governed protection and simulation layer spanning GUARDIAN, XUNIA, ZYRA, SHADOW GLASS, and GLASS ONION.

## Goal

Build a multi-domain defensive system that ingests authorized/public observations, normalizes provenance, assesses hazards, proposes protective actions on owned or explicitly authorized assets, visualizes incidents in XUNIA, and exercises those workflows in an inert/synthetic range.

The system must remain structurally unable to perform weapon target selection, fire control, guidance, initiation, explosive design, autonomous engagement, or counter-intrusion against third-party systems.

## Existing ecosystem foundations

This design extends existing repository controls rather than replacing them:

- `safety-shield/policies/infrastructure-resilience.json` already defines GREEN/AMBER/RED/BLACK states, fail-closed handling, simulation before consequential mutation, rollback, least privilege, append-only evidence, human override, and external dispatch disabled by default.
- `safety-shield/ontology/safety-shield.ttl` already models SHADOW GLASS as the outer trust/policy boundary and GLASS ONION as the observable authority/evidence model.
- `docs/GUARDIAN_ACTIVE_DEFENSE_BLUEPRINT.md` defines defensive response inside an authorized boundary and prohibits external counter-intrusion.
- `va3lm/docs/RVIA_FEDERAL_INTEL.md` already catalogs NGA/NGP public resources and the official `ngageoint` open-source surface for GEOINT standards, GeoPackage, Hootenanny, and MAGE.

## Public patent references

Public patents are architecture/threat-model references only. They do not grant affiliation, authority, implementation rights, or permission to reproduce controlled capabilities.

- US 12,729,938 B2: high-level reference for protecting optical sensing hardware and modular sensor exposure/protection concepts.
- US 12,729,939 B2: threat-model reference only. No warhead construction, fragmentation geometry, initiation, firing solution, guidance, target selection, or engagement logic enters this repository.
- US 12,722,816 B2: high-level reference for distributed sensing and protective alerting.

## Program structure

The program is split into three independently testable subsystems.

### 1. GUARDIAN SHIELD

Purpose: convert trusted observations into defensive actions on owned or explicitly authorized infrastructure.

Core responsibilities:

- validate observation provenance, identity, time, scope, and integrity;
- correlate observations without asserting unsupported attribution;
- produce `HazardAssessment` and `ResponseProposal` objects;
- require simulation for consequential mutations;
- require human approval for material actions;
- execute only allow-listed protective actions inside the authorized boundary;
- generate append-only `DefenseReceipt` evidence.

Allowed action classes:

- isolate a managed endpoint/workload;
- revoke or rotate owned credentials, sessions, tokens, or secrets;
- apply firewall/WAF/EDR/IAM/service-mesh deny rules to owned systems;
- rate-limit or disable an exposed owned service;
- quarantine suspicious files/processes on managed systems;
- sandbox suspicious input;
- activate deception assets inside the protected environment;
- preserve logs, snapshots, hashes, and incident evidence;
- fail over to approved backup services/communications;
- restore verified recovery points and validate restoration;
- trigger operator alerts, check-ins, shelter/evacuation, or emergency procedures.

Explicitly absent action classes:

- weapon target selection;
- strike/engagement recommendation;
- fire-control calculations;
- guidance or interceptor command generation;
- initiation/detonation control;
- explosive/fragmentation design;
- external exploitation or counter-hacking;
- destructive action against third-party systems.

### 2. XUNIA DEFENSE GRID

Purpose: present a provenance-first common operating picture for defensive awareness and incident response.

Every displayed object/event must separate observed facts from model inference.

Required fields:

- `event_id`
- `observation_id`
- `source_id`
- `source_type`
- `observed_at`
- `received_at`
- `provenance_status`
- `confidence`
- `state` (`GREEN|AMBER|RED|BLACK`)
- `geometry` or coarse geospatial location when appropriate
- `location_precision_class`
- `evidence_refs`
- `assessment_summary`
- `recommended_protective_action`
- `fact_or_inference`
- `live_state` (`LIVE|DELAYED|RECONSTRUCTED|MODELED|PARTIAL|UNAVAILABLE`)

Privacy rules:

- precise human location is suppressed by default;
- personal/biometric telemetry is never exported to public XUNIA views;
- public and government-facing exports must contain only approved data classes;
- unsupported attribution is labeled hypothesis, not fact.

Interoperability targets:

- GeoJSON export;
- GeoPackage-compatible export;
- MAGE-compatible observation mapping where feasible;
- Hootenanny-compatible geospatial attributes/provenance where feasible;
- no claim of NGA partnership, endorsement, or authorization without separate written agreement.

### 3. GUARDIAN RANGE

Purpose: validate policies, response timing, data contracts, and operator workflows without live weapons, destructive payloads, or unauthorized targets.

Range scenarios are synthetic or inert and include:

- credential compromise;
- malware containment on owned test hosts;
- service abuse and rate-limit events;
- sensor/provenance tampering;
- infrastructure outage and recovery;
- simulated physical hazard tracks;
- degraded communications;
- false-positive and conflicting-sensor cases;
- RED/BLACK recovery exercises.

The range can model a hostile or high-energy event as an abstract hazard object, but cannot encode weapon firing solutions, guidance, payload effects optimization, initiation logic, or target engagement.

## Domain model

### `SensorObservation`

Immutable normalized observation.

Required fields:

- `observation_id: str`
- `source_id: str`
- `source_type: str`
- `observed_at: RFC3339 str`
- `received_at: RFC3339 str`
- `payload_hash: sha256 str`
- `provenance_status: VERIFIED|PARTIAL|UNVERIFIED|REJECTED`
- `confidence: float 0..1`
- `scope_id: str`
- `fact_or_inference: FACT|INFERENCE`
- optional geospatial geometry and precision class

### `HazardAssessment`

- `assessment_id: str`
- `observation_ids: list[str]`
- `hazard_class: str`
- `impact: LOW|MODERATE|HIGH|CRITICAL`
- `likelihood: float 0..1`
- `state: GREEN|AMBER|RED|BLACK`
- `attribution_status: NONE|HYPOTHESIS|VERIFIED_EXTERNAL_SOURCE`
- `rationale: str`

### `ResponseProposal`

- `proposal_id: str`
- `assessment_id: str`
- `action_class: str`
- `target_resource_id: str`
- `authorized_boundary_id: str`
- `material_action: bool`
- `simulation_required: bool`
- `simulation_receipt_id: str | null`
- `rollback_plan_id: str | null`
- `human_approval_required: bool`
- `expires_at: RFC3339 str`

### `AuthorizationGrant`

- `grant_id: str`
- `proposal_id: str`
- `approver_identity: str`
- `scope_id: str`
- `approved_action_class: str`
- `approved_target_resource_id: str`
- `issued_at: RFC3339 str`
- `expires_at: RFC3339 str`

### `DefenseReceipt`

- `receipt_id: str`
- `proposal_id: str`
- `grant_id: str | null`
- `executed: bool`
- `execution_status: ALLOWED|DENIED|FAILED|SUCCEEDED|ROLLED_BACK`
- `started_at: RFC3339 str`
- `completed_at: RFC3339 str`
- `evidence_refs: list[str]`
- `post_action_validation: PASS|FAIL|NOT_RUN`
- `rollback_receipt_id: str | null`

## Policy contract

The deterministic policy gate must enforce these invariants:

1. Unknown or unverified authorization fails closed.
2. Unknown target ownership/scope fails closed.
3. External dispatch is disabled by default.
4. Consequential mutation requires a successful simulation receipt.
5. Material actions require an unexpired human authorization grant.
6. Mutating actions require a rollback plan unless the action is explicitly classified as non-mutating.
7. A model score alone cannot authorize action.
8. Weapon-control and external counter-intrusion action classes do not exist in the executable action registry.
9. Every decision produces an append-only evidence record, including denials.
10. Recovery is incomplete until post-change validation passes.

## State behavior

### GREEN

- observe;
- normalize;
- correlate;
- display;
- recommend low-risk reversible protective actions.

### AMBER

- increase logging/telemetry;
- require operator review for material changes;
- run simulation/dry-run;
- preserve evidence;
- prepare rollback/recovery assets.

### RED

- allow approved defensive containment on owned resources;
- revoke compromised owned credentials/tokens;
- isolate managed endpoints/workloads;
- disable exposed owned services where approved;
- preserve evidence;
- initiate recovery/failover;
- trigger safety/escalation workflows.

### BLACK

- freeze nonessential mutation;
- quarantine affected locally governed routes/resources;
- protect control-plane credentials and evidence stores;
- require explicit recovery authorization;
- restore only from verified recovery points;
- validate before re-entering RED/AMBER/GREEN.

## Proposed repository footprint

```text
guardian/
  defense_grid/
    __init__.py
    models.py
    policy.py
    registry.py
    receipts.py
    simulation.py
    xunia_export.py
    schemas/
      sensor-observation.schema.json
      hazard-assessment.schema.json
      response-proposal.schema.json
      authorization-grant.schema.json
      defense-receipt.schema.json
      xunia-defense-layer.schema.json
    policies/
      authorized-boundary.json
      protective-actions.json
      physical-hazard-policy.json
    fixtures/
      synthetic-observations.json
      synthetic-hazards.json

safety-shield/
  ontology/
    guardian-defense-grid.ttl

scripts/
  validate_guardian_defense.py

tests/
  guardian/
    test_models.py
    test_policy.py
    test_registry.py
    test_simulation.py
    test_xunia_export.py
    test_receipts.py

.github/workflows/
  guardian-defense-gate.yml

docs/
  GUARDIAN_XUNIA_DEFENSE_GRID.md
```

## Implementation boundaries

### Phase 1: policy and data contracts

Deliverables:

- schemas;
- Python domain models;
- authorized-boundary policy;
- safe executable action registry;
- deterministic validator;
- unit tests.

No live mutating connector is introduced in Phase 1.

### Phase 2: XUNIA export

Deliverables:

- privacy-preserving defense-layer exporter;
- GeoJSON output;
- GeoPackage-ready record mapping;
- LIVE/DELAYED/RECONSTRUCTED/MODELED/PARTIAL/UNAVAILABLE state handling;
- tests proving precise-person-location suppression.

### Phase 3: GUARDIAN Range

Deliverables:

- synthetic scenario loader;
- simulation receipt generation;
- policy/fault-injection tests;
- RED/BLACK transition exercises;
- no live weapon or destructive action adapters.

### Phase 4: defensive adapters

Only after the prior phases pass CI, add narrowly scoped adapters for owned infrastructure such as local firewall configuration, session/token revocation, workload isolation, or service failover. Each adapter must have its own explicit scope, dry-run mode, rollback path, audit receipt, and human approval contract.

## Testing strategy

Tests must prove both positive behavior and forbidden-state behavior.

Required negative tests:

- unverified source cannot authorize action;
- unknown boundary cannot mutate;
- expired authorization cannot mutate;
- missing simulation blocks consequential mutation;
- missing rollback blocks mutation;
- model inference cannot be promoted to observed fact;
- precise human location is removed from public XUNIA export;
- prohibited action names are rejected during registry load;
- external counter-intrusion cannot be represented as executable action;
- weapon-control semantics cannot be registered as executable actions.

Required positive tests:

- verified observation can create a hazard assessment;
- approved locally governed containment can produce a successful receipt;
- denied action produces an auditable receipt;
- simulation receipt can satisfy the simulation precondition;
- rollback and post-change validation produce a recovery receipt;
- GeoJSON/XUNIA export preserves provenance and confidence metadata.

## CI gate

`guardian-defense-gate.yml` must run on changes to GUARDIAN defense code, schemas, policies, ontology, validators, and workflow files.

The gate must:

1. run focused GUARDIAN tests;
2. compile the deterministic validator;
3. validate JSON schemas/policies;
4. fail when prohibited executable action semantics appear;
5. fail when external dispatch default is changed from disabled;
6. fail when human approval or simulation requirements are removed;
7. fail when public XUNIA export allows precise personal location by default.

## Government and NGA positioning

The system is an unclassified defensive GEOINT/safety prototype unless a separate agreement says otherwise.

The repository may interoperate with public NGA/NGP standards and `ngageoint` open-source software, but must not claim:

- NGA sponsorship;
- NGA certification;
- NGA partnership;
- government authorization;
- classified connectivity;
- operational targeting/tasking authority.

Government-facing demonstrations should emphasize:

- provenance;
- interoperability;
- human-machine teaming;
- defensive hazard awareness;
- infrastructure resilience;
- public/authorized data handling;
- reproducible evidence;
- auditable human authority.

## Acceptance criteria

The design is complete when implementation can demonstrate all of the following:

- `SensorObservation -> HazardAssessment -> ResponseProposal -> SimulationReceipt -> AuthorizationGrant -> DefenseReceipt` works deterministically;
- unknown identity/provenance/scope/integrity fails closed;
- executable actions are limited to protective actions on owned or authorized resources;
- no weapon-control or external counter-intrusion action exists in the executable registry;
- material actions require valid human approval;
- consequential mutations require simulation and rollback metadata;
- XUNIA clearly distinguishes fact from inference;
- privacy-sensitive location is suppressed by default;
- append-only evidence covers approvals, denials, execution, rollback, and recovery;
- focused CI tests pass;
- documentation clearly states the defensive scope and government/partner boundary.
