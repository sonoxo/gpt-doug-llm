# GPT-Doug Quantum Warfighter Ontology
## Isolated Research + Simulation Architecture Specification

**Version:** 1.0.0 — design for review  
**Date:** 2026-10-12  
**Status:** DESIGN SPECIFICATION — NOT IMPLEMENTED OR AUTHORIZED FOR OPERATIONAL USE  
**Repository:** sonoxo/gpt-doug-llm  
**Target:** GPT-Doug-LLM + PINEAL + ZYRA / ZYRA-MSS  
**Selected architecture:** Isolated, offline-first mathematical research and synthetic simulations. Only explicitly human-reviewed, reproducible results enter a dedicated research ontology overlay.

> **Reality boundary:** “Quantum” in this proposal means classical quantum-inspired mathematics/simulation, not quantum-computing hardware or speedup. The 6D/10D/11D representations are computational or mathematical projections, not physical access to additional dimensions. String-inspired geometry is educational and exploratory, not a validated physical discovery. The platform is not a Department of Defense system, accreditation, certification, authority to operate, targeting capability, or weapons-control system.

---

## 1. Outcome and definition of done

The goal is an inspectable, low-cost, local-first **Warfighter Ontology research subsystem** for synthetic operational support and defensive-system assurance. It supports:

1. Typed ontology relationships for equipment classes, training coverage, maintenance, supply continuity, communications health, software integrity, cybersecurity posture and recovery.
2. Bounded, deterministic synthetic scenario evaluation and exploratory mathematical models.
3. A clearly isolated mathematical research environment using existing Bio-Hilbert exact arithmetic, an optional classical quantum-inspired state-vector demonstrator, and optional 10D/11D geometry visualization.
4. Provenance, repeatable verification, and explicit human acceptance before a result is published into the research ontology.
5. Research-only retrieval from GPT-Doug, PINEAL, and ZYRA dashboards without any implicit elevation to operational data, policy decisions, or readiness authority.
6. Terminal JSON/status access, then optional 6D Blender visualization **only after its separate design and implementation are approved**.

**Success is measurable:** a reviewer runs an offline synthetic fixture, independently replays the verification certificate, approves the artifact through an explicit review operation, sees its typed record and provenance link in a research-only overlay, and confirms that the original ZYRA-MSS ontology, real readiness values, and any connected service remain unchanged.

The initial deliverable is engineering software for demonstration, education, analysis and internal evaluation. It is not intended for classified networks, CUI, export-controlled data, live troop/equipment telemetry, weapons data, real-time defense decision-making, or operational deployment.

## 2. Verified repository foundation (main branch)

The design builds on verified project code and documentation, not assumed implementations:

| Existing source | What exists | Integration decision |
| --- | --- | --- |
| safety-shield/ontology/zyra-mss-v1.json | MissionRequest, EvidenceObject, TaskObject, AssetState, ReadinessState, RiskObject, AccessPolicy, AgentRecommendation, AnalystDecision, AuditEvent, permitted/reviewed/blocked actions | Keep authoritative mission-support contract unchanged; reuse type semantics; create a separate versioned extension/overlay |
| docs/ZYRA_MSS.md and scripts/zyra_mss.py | Advisory workflow, synthetic demonstrations and a local ontology diagnostic | New command may wrap read-only summaries; do not silently replace existing commands |
| integrations/gpt-doug-pineal/src/pineal/store.py | Local SQLite memories, version checks, provenance, append-only hash-chained audit records | Use a narrowly scoped research namespace only after explicit approval; an audit hash is not an authenticated digital signature |
| integrations/gpt-doug-pineal/src/pineal/bridge.py | Opt-in read-only adapters for GPT-Doug JSONL memory and config/global-ontology.json | Treat as read-only lookup; it does not automatically index arbitrary new ontologies |
| integrations/gpt-doug-pineal/src/pineal/federation.py | Local-only federation registry and synthetic-only warfighter-defense-si metrics | Retain exact synthetic-only allowlist, never open it to real defense information |
| integrations/gpt-doug-pineal/src/pineal/cli.py | Local CLI: put, find, context, heartbeat, observe, dashboard, audit, etc. | Reuse normal audit and store mechanisms only after explicit publication; do not create implicit auto-sync |
| research_lab/bio_hilbert.py and research_lab/BIO_HILBERT_DIMENSIONS.md | Six-channel exact-rational finite Galerkin Euler dynamics with analytical estimates; MAX_MODES=128, MAX_STEPS=8 | Mathematical kernel can run in isolation; do not reinterpret its six biological-metaphor labels as operational facts |
| research_lab/multidimensional_ontology.json | Rational linear models, Lyapunov certificates, finite-lattice witnesses, provenance constraints | Reuse a research-evidence vocabulary and verification conventions |
| research_lab/bio_gpt_ontology.json | A conceptual role-mapping layer over Bio-Hilbert; no physical neural interface | Reference as a mathematical analogy only |
| workers/xqe.py | A classical candidate/simulate/score/verify workflow; its verify() actually dispatches a task | **Never call XQE.run() or XQE.verify() from the isolated research subsystem.** Reuse the conceptual pipeline only, with new pure functions and no dispatch |
| docs/MIL_READINESS.md | Engineering roadmap and explicit nonauthorization boundary | Carry forward governance, provenance and non-ATO caveats |

The previous 6D Blender/terminal design exists on a *separate* design branch (design/pineal-biochip-6d-blender-20261012). No live Blender integration is assumed or required for this specification.

## 3. Architecture decision and alternatives

**Chosen: a versioned ontology extension + isolated simulation package + human-controlled research overlay.**

Alternative A (rejected): directly modify the canonical ZYRA-MSS ontology and its readiness engine with mathematical experiment outputs. This couples unvalidated research to operational support and creates rollback/regression risks.

Alternative B (rejected): a completely independent Warfighter graph with its own policy, identity and audit infrastructure. This duplicates governance and weakens integration.

Chosen design preserves the mature ZYRA object vocabulary while making experimental results demonstrably non-authoritative. Optional adapters provide explicit interoperability with PINEAL. Implementation proceeds in separately testable increments, not as an all-at-once rewrite.

### 3.1 Logical component diagram

~~~text
                         SYNTHETIC / PUBLIC REFERENCE FIXTURES
                                        |
                               local scope validation
                                        |
                            +-----------v-------------+
                            | WARFIGHTER ONTOLOGY v1   |
                            | typed schema + links     |
                            | invariant / source gate  |
                            +-----------+-------------+
                                        |
                             read-only scenario view
                                        |
                            +-----------v-------------+
                            | ISOLATED RESEARCH LAB   |
                            | pure, offline, bounded  |
                            |                          |
                            | A. scenario baseline     |
                            | B. Bio-Hilbert 6-channel |
                            | C. classical statevector |
                            | D. optional 10D/11D geo  |
                            +-----------+-------------+
                                        |
                           deterministic run + artifact
                                        |
                             +----------v----------+
                             | VERIFICATION GATE   |
                             | replay + bounds     |
                             | hashes + labels     |
                             | source provenance   |
                             +----------+----------+
                                        |
                             RESEARCH QUARANTINE
                                        |
                            +-----------v-----------+
                            | HUMAN REVIEW RECORD   |
                            | approve / reject      |
                            | signed when supported |
                            +------+----------+-----+
                                   |          |
                                 reject    approve
                                   |          |
                              retain /       v
                              archive   RESEARCH OVERLAY
                                        (not readiness)
                                             |
                   +-------------------------+------------------+
                   |                         |                  |
              GPT-Doug                 PINEAL approved      ZYRA read-only
              research query           memory projection     dashboard
                   |                         |                  |
                   +-------------------------+------------------+
                                             |
                                audit + status/visualization
~~~

**Hard trust boundary:** arrows toward the research overlay can carry an approved *claim about a simulation*. No arrow exists from the overlay to an operational readiness field, asset control, ZYRA permission mutation, dispatch queue, weapons system, personnel identity system, or real-time command network.

## 4. Functional scope: two Warfighter support domains

### 4.1 Operational-support domain (synthetic only in release v1)

- Model **EquipmentClass** and illustrative counts/maintenance status, not identifiable real assets.
- Model **MaintenanceRequirement**, **MaintenanceExercise**, deferred service and simulated completion.
- Model **SupplyCategory**, **SupplyConstraint**, depot/capacity *categories* and training-only continuity examples.
- Model **TrainingRequirement**, **TrainingExercise** and aggregate completion/coverage.
- Model **ContinuityExercise** and non-sensitive recovery dependencies.
- Generate explanatory summaries showing what *hypothetical* data, assumptions and evidence drive an exercise outcome.

Never provide live deployments, troop/equipment positions, mobilization routes, adversary exposure, combat supply priorities or real mission schedules.

### 4.2 Defensive-systems domain (synthetic only in release v1)

- Model **DefensiveControl** and synthetic patch-compliance, recovery readiness and zero-trust coverage.
- Model **CommunicationsServiceClass**, **HealthObservation** and aggregate availability, not packet content or actual topology.
- Model **SensorHealthClass**, simulator health, synthetic fault states, not live classified sensor data.
- Model **DefensiveIncidentExercise**, evidence and analyst-reviewable recovery hypotheses.
- Model **SoftwareArtifactEvidence**, allowed component provenance and verification state.
- Run only bounded, offline, non-destructive exercises; never scan, probe, exploit or control real endpoints.

Existing PINEAL warfighter-defense-si allowable synthetic metric identifiers are: patch_compliance_pct, training_readiness_pct, sensor_health_pct, simulation_alerts, zero_trust_coverage_pct. This release cannot enlarge that allowlist or accept non-synthetic defense observations by indirect pathways.

## 5. Ontology object model

### 5.1 Namespace and ownership

- **Authority graph:** existing ZYRA_MSS_V1 remains intact, authoritative for the existing software engineering contract.
- **Extension schema:** WARFIGHTER_RESEARCH_V1, kept under safety-shield/ontology/warfighter-research-v1.json; declares types/links and validation policy, but is not an authority override.
- **Instance overlay:** generated, verified and reviewed records under an explicitly dedicated local research data directory, not in version-controlled configuration or ZYRA_MSS_V1.
- **PINEAL projection:** namespace "warfighter_research" stores approved minimal triples with artifact pointers and hashes; storing a triple is not the same as changing ZYRA-MSS's authority graph.
- **Resolution:** for cross-domain queries prefer source-grounded ZYRA schema, then approved research overlay, then unapproved quarantined experiments only when explicitly requested as such. Never conflate these.

### 5.2 New types and mandatory fields

Common fields on *each persisted instance*: id (namespaced), schema_version, type, source_kind, classification, synthetic, created_at (UTC ISO8601), provenance, source_refs (array), evidence_status, confidence_scope, record_sha256. Unknown source/consent/authority is rejected rather than guessed.

| Object type | Domain | Required domain-specific fields |
| --- | --- | --- |
| EquipmentClass | operational | name, count_band, synthetic_state, exercise_id |
| MaintenanceRequirement | operational | equipment_class_ref, category, due_phase, status |
| SupplyCategory | operational | category, capacity_band, availability_band, unit |
| SupplyConstraint | operational | supply_category_ref, constraint_kind, severity_band |
| TrainingRequirement | operational | training_kind, completion_criteria, evidence_refs |
| TrainingExercise | operational | training_requirement_ref, cohort_aggregate, simulated_completion_pct |
| ContinuityExercise | both | scenario_ref, recovery_objective, simulated_result_ref |
| DefensiveControl | defensive | control_family, control_status, simulated_coverage_pct |
| CommunicationsServiceClass | defensive | service_class, aggregate_status, simulated_uptime_pct |
| SensorHealthClass | defensive | category, synthetic_health_pct, observed_at |
| DefensiveIncidentExercise | defensive | incident_class, simulated_impact, proposed_recovery_ref |
| SoftwareArtifactEvidence | defensive | artifact_digest, source, integrity_check, status |
| ResearchScenario | research | domains, fixture_ref, assumptions, mathematical_models, seed |
| ResearchModel | research | model_family, formal_assumptions, implementation_digest, limits |
| SimulationRun | research | scenario_ref, model_ref, input_digest, output_digest, run_status |
| MathCertificate | research | run_ref, certificate_kind, verification_method, check_status |
| ResearchEvidence | research | run_ref, certificate_refs, claim_text, scope_of_claim, limitations |
| ReviewDecision | governance | evidence_ref, disposition, reviewer_ref, timestamp, rationale |
| ApprovedResearchFinding | overlay | evidence_ref, review_ref, publication_id, evidence_label, supersedes |
| ProvenanceSource | governance | source_uri_or_local_id, rights_basis, source_kind, captured_at |
| AuditTrailEvent | governance | event_type, actor_ref, timestamp, payload_digest, previous_digest |

The existing MissionRequest, TaskObject, AssetState, ReadinessState, RiskObject, EvidenceObject, AgentRecommendation, AnalystDecision and AuditEvent remain defined by the base ontology and are **not redefined**. Research records may refer to existing **type definitions**, but cannot create or modify authoritative operational instances.

Additional schema definitions belong to versioned data files validated by code rather than dynamically executed expressions embedded in ontology data.

### 5.3 Typed edge contract

| Subject | Relationship | Object | Rule |
| --- | --- | --- | --- |
| EquipmentClass | HAS_REQUIREMENT | MaintenanceRequirement | same synthetic exercise |
| SupplyConstraint | AFFECTS_CATEGORY | SupplyCategory | supported by fixture |
| TrainingExercise | EVALUATES | TrainingRequirement | aggregate synthetic only |
| DefensiveControl | CONSTRAINS | CommunicationsServiceClass | synthetic exercise, not real network configuration |
| DefensiveIncidentExercise | HAS_RECOVERY_EXERCISE | ContinuityExercise | recovery proposal only |
| ResearchScenario | USES_MODEL | ResearchModel | explicit version |
| ResearchScenario | HAS_INPUT_SOURCE | ProvenanceSource | synthetic/public allowlist |
| SimulationRun | INSTANTIATES | ResearchScenario | immutable run/fixture references |
| SimulationRun | EVALUATED_BY | MathCertificate | verifier and digest required |
| ResearchEvidence | SUPPORTED_BY | MathCertificate | scope limited to mathematical model |
| ResearchEvidence | DERIVED_FROM | SimulationRun | exact run provenance |
| ReviewDecision | REVIEWS | ResearchEvidence | explicit human action |
| ApprovedResearchFinding | PUBLISHED_FROM | ResearchEvidence | only approved, verified records |
| ApprovedResearchFinding | AUTHORIZED_BY | ReviewDecision | decision must be APPROVED |
| ApprovedResearchFinding | REQUIRES_SOURCE | ProvenanceSource | no orphaned evidence |
| AuditTrailEvent | RECORDS_REVIEW | ReviewDecision | append-only lineage |

An edge is invalid if its endpoint type is wrong, the referenced ID does not exist, it crosses a forbidden classification boundary, it creates a self-referential approval, or it attempts to attach unapproved evidence to a mission-support readiness value.

## 6. Data taxonomy, classification, and provenance

**Three axes must never be merged:**

1. **Data classification and source rights:** PUBLIC or SYNTHETIC only (for release v1). SYNTHETIC requires true synthetic flag. Non-public data cannot become PUBLIC by renaming or summarizing it. No CUI, export-controlled, classified, private location or personal/medical records.
2. **Evidence status:** UNSUBSTANTIATED, COMPUTED_UNVERIFIED, MATHEMATICALLY_VERIFIED, HUMAN_REVIEWED, REJECTED, REVOKED. "MATHEMATICALLY_VERIFIED" means the given formal computation passed—not that a real-world warfighter capability exists or works.
3. **Authority status:** RESEARCH_ONLY in release v1, including approved findings. Neither confidence, verified code, an auditor badge, a reviewer's approval, nor math proof changes this to operational authority.

Each imported file must have its own rights_basis, source identifier, local path or public URI, capture timestamp, content hash, license/usage condition when known, origin kind and validation status. Default source access is none. Synthetic fixtures are clearly identifiable and cannot be presented as current defense telemetry.

A SHA-256 digest provides integrity against accidental changes when recomputed against a trusted expected digest; it is not a substitute for an authenticated signature, identity proof, immutable remote audit or regulatory authorization.

## 7. Research engines and mathematical truth conditions

All engines run in an **explicit local, offline, non-executing-sandbox-style boundary**: load strict declarative data; never evaluate arbitrary Python from scenarios; no dynamic imports, subprocesses, network calls or arbitrary path reads within a simulation. Run limits, normalization and serialization occur at the boundary.

### 7.1 Engine A — baseline deterministic scenario model

First engine uses synthetic, aggregate inputs and fully published arithmetic (e.g., one scenario's patch-compliance projection or training-coverage change). No weighted "mission readiness" score is emitted by default. Outputs are descriptive comparisons of the provided synthetic fixture.

- Inputs: scenario fixture, explicit assumptions and bounded perturbations.
- Outputs: before/after synthetic aggregate metrics, assumptions, sensitivity table, exact formula ID.
- Uncertainty: label uncertainty about arbitrary assumptions as a sensitivity exercise, not statistical confidence about operational reality.
- Reproducibility: canonical input JSON digest, deterministic sort order, pinned model version, no hidden randomness.

### 7.2 Engine B — Bio-Hilbert exact-rational model

Reuse the **existing** six-channel mathematical kernel under its existing assumptions, rather than inventing an "infinite computer." Mathematical space is H = ell^2(N; R^6). The implementation computes only finite truncations; existing bounds include 1–128 modes and at most 8 exact Euler steps per run.

For each mode j, the toy vector field is:

~~~text
dX_j/dt = -alpha*X_j
          + kappa*(X_(j-1) - 2*X_j + X_(j+1))
          + Omega*X_j
          + beta*sat(X_j)
sat(z) = z/(1 + |z|), componentwise
~~~

When alpha > beta >= 0 and kappa >= 0, the stated analytical decay certificate pertains only to the specified equation, with extra step-size restrictions for the exact Euler contraction certificate. The engine must call existing canonical validation/replay rather than copy or relax the model's certificate logic.

The original labels ("neural", "metabolic", "immune", "epigenetic", "sensory", "memory") remain conceptual mathematical coordinates. The Warfighter ontology may attach **explicit, declared scenario feature aliases for visualization** but cannot claim physical, biomedical, or operational calibration. No output from this mathematical model is permitted to rewrite actual readiness, network security posture or equipment state.

### 7.3 Engine C — classical quantum-inspired simulator (optional second milestone)

Implement small, purely classical, normalized complex state vectors with documented matrices and gates, deterministic sampling seeds, and norm/unitarity checks. For example, at most **6 simulated qubits** (64 complex amplitudes) initially. Classical linear algebra does not imply a quantum chip, error-corrected quantum computer or quantum speedup.

- Exact declared gate set and operation count caps; reject nonunitary gates when a unitary gate is required.
- State preparation, matrix multiplication, projective-probability calculation, normalization and a deterministic simulation report are transparent.
- If a sampling mode is enabled, store RNG algorithm + seed + sample count; probability calculations remain separate from sampled frequencies.
- Full numerical tolerance and backend versions must accompany any floating-point result.
- No fabricated quantum hardware, entanglement distribution, remote provider access, encryption breakthrough, or battlefield utility claims.

**XQE boundary:** existing workers/xqe.py can dispatch real tasks during verify(); it must never be invoked by this simulator. Research-specific "generate, simulate, score, select, verify" code shall be pure and offline, with selection of *simulated candidates only*.

### 7.4 Engine D — string-inspired higher-dimensional geometry (optional third milestone)

Support educational coordinate spaces in **R^6, R^10, and R^11** and bounded toy compactifications/projections into R^3 for Terminal/Blender. Store the declared ambient dimension, coordinate basis, projection matrix, compactification radii (if any), assumptions and a reversible *data* transform when mathematically valid. A 3D rendering need not be reversible, and must say so.

These are mathematical geometry/visualization artifacts inspired by high-dimensional approaches to theoretical physics, **not** evidence of physical extra dimensions, a solution to string theory, experimental quantum gravity or a scientific discovery. Optional animation is visual inference of a toy model, not a sensor output.

### 7.5 Cross-model contracts

- Models exchange only schema-validated numeric objects, not executable code or hidden agent prompts.
- Each model has an independent version, parameter digest, documented assumptions, method, resource ceiling and independent verifier.
- An engine returns ERROR or INCONCLUSIVE rather than silently substituting a different model, dropping constraints or claiming a proof.
- Comparing unlike models must disclose different units, assumptions and outputs; no forced universal combined readiness rank.
- A certificate verifies the *particular model/run*. Reviewers cannot promote a statement broader than the certificate and evidence support.

## 8. Scenario-to-result data contract

The prototype records use UTF-8 canonical JSON with sorted keys and explicitly versioned schemas. Example **synthetic** request (numbers are artificial):

~~~json
{
  "schema_version": "1.0.0",
  "scenario_id": "wr:scenario:demo-0001",
  "source_kind": "SYNTHETIC",
  "classification": "SYNTHETIC",
  "synthetic": true,
  "domains": ["training", "defensive-systems"],
  "fixture": {
    "training_readiness_pct": 68,
    "patch_compliance_pct": 74,
    "sensor_health_pct": 91
  },
  "assumptions": [
    "All values are invented for an offline exercise",
    "No external connectivity or real systems"
  ],
  "model_id": "synthetic-baseline-v1",
  "seed": 0
}
~~~

The resulting artifact envelope must contain at minimum:

~~~json
{
  "schema_version": "1.0.0",
  "id": "wr:run:demo-0001",
  "type": "SimulationRun",
  "classification": "SYNTHETIC",
  "source_kind": "SYNTHETIC",
  "synthetic": true,
  "authority": "RESEARCH_ONLY",
  "scenario_ref": "wr:scenario:demo-0001",
  "model": {
    "id": "synthetic-baseline-v1",
    "version": "1.0.0",
    "implementation_sha256": "sha256-of-reviewed-code"
  },
  "input_sha256": "sha256-of-canonical-input",
  "output_sha256": "sha256-of-canonical-output",
  "verification": {
    "status": "PENDING",
    "verifier_version": "1.0.0",
    "certificate_ref": null
  },
  "review": {
    "status": "UNREVIEWED",
    "review_record_ref": null
  },
  "publication": {
    "status": "QUARANTINED",
    "namespace": "warfighter_research"
  }
}
~~~

Those example digest strings are **illustrative placeholders**, not valid digests; validator requires actual 64-character lowercase hex SHA-256 fields before verification/promotion. The artifact must also record an actual created_at ISO8601 UTC timestamp, source_refs, dataset right/consent metadata, run limits, code commit identifier, complete numerical outputs, engine environment and deterministic replay instructions. The example omits them for legibility, not because they are optional in persisted records.

**No raw prompts, API keys, personal records, hidden chain-of-thought, host secrets or privileged network endpoints** appear in the research artifact.

## 9. Verification, review and publication state machine

~~~text
DRAFT
  | schema + data-rights validation
  v
QUARANTINED
  | offline computation (bounded)
  v
COMPUTED_UNVERIFIED
  | exact replay and model-specific checks
  v
VERIFIED_FOR_MODEL
  | named, explicit human decision
  +----> REJECTED (audit + no publish)
  |
  v
HUMAN_APPROVED
  | promotion transaction & digest checks
  v
PUBLISHED_RESEARCH_ONLY
  |
  +----> SUPERSEDED / REVOKED (immutable history + tombstone)
~~~

**Promotion conditions (all required):**

1. Typed ontology schema and every relationship pass validation; no dangling IDs, unexpected fields, disallowed nodes, unsafe operational references or path traversal.
2. Source_kind is SYNTHETIC or expressly permitted PUBLIC research material; Warfighter PINEAL observations remain synthetic only. For release v1, only synthetic scenario examples can publish into the Warfighter namespace.
3. Verifier reproduces applicable numeric results and checks the exact certificate where available. A deterministic output-digest mismatch blocks promotion.
4. Claim text is limited to that certificate's applicability, with assumptions and limitations visible.
5. A human operator opens the artifact and records an explicit approval or rejection with reviewer identifier, UTC timestamp, rationale, decision and snapshot digest. Review is an application-level workflow, not an independently verified identity or DoD authorization.
6. Immediately before publication, revalidate current schema, unchanged content digest, decision binding and denylist, then atomically append a publication event.
7. Build the versioned overlay projection from validated publication events. On failure, leave artifact QUARANTINED or NOT_PUBLISHED; repair/replay must be idempotent.
8. Optionally publish a **minimal approved summary** as a PINEAL memory triple under "warfighter_research". Never write to canonical ZYRA authority files, existing "general" namespace, readiness fields or PINEAL federation observations as a side effect.
9. Any edit to result content, limitations, verifier or model version invalidates prior approval, creating a new reviewed version.
10. REVOKED findings disappear from normal retrieval while remaining in the immutable local audit history; prevent stale PINEAL projections from implying current validity.

**Two-phase publication:** (a) append signed-or-at-least-hash-bound local review and publication-event intent with a unique idempotency key; (b) build/rebuild research overlay index, then project concise records to PINEAL if explicitly enabled. A projection failure must not falsely label PINEAL as synchronized; report PARTIALLY_PROJECTED and safely retry. Hash chaining alone is not tamper-proof against an actor who can rewrite both the data and hashes; stronger attestation is a separately reviewed enhancement.

## 10. Service contracts / command-line interface (proposed)

No new commands below are claimed to exist yet. Proposed user interfaces:

~~~text
bash scripts/doug-max warfighter status
bash scripts/doug-max warfighter ontology --validate
bash scripts/doug-max warfighter scenario validate path/to/synthetic.json
bash scripts/doug-max warfighter simulate path/to/synthetic.json --engine baseline --offline
bash scripts/doug-max warfighter simulate path/to/hilbert.json --engine bio-hilbert --offline
bash scripts/doug-max warfighter verify path/to/run.json
bash scripts/doug-max warfighter review path/to/run.json --decision approve --rationale "..."
bash scripts/doug-max warfighter publish path/to/run.json --namespace warfighter_research
bash scripts/doug-max warfighter findings --approved-only
bash scripts/doug-max warfighter doctor
~~~

- Status/ontology/verify/findings are read-only and have stable JSON output with optional human-readable rendering.
- Simulate writes only to an explicitly named local quarantine/workspace directory. No daemon, recurring action, external API, service scanner or dispatch is started.
- Review/publish require separate explicit operator commands; never happen during analysis, scheduled heartbeat, retrieval, visualization or AI recommendation.
- Publication path must enforce local workspace confinement and safe path resolution; cannot write arbitrary user-selected system paths.
- Stable exit codes: 0=success, 2=invalid request/data, 3=verification failed, 4=not approved, 5=resource limit, 6=unavailable optional component, 7=publication conflict.
- JSON output includes truth flags: simulated, mathematical_verification, human_reviewed, published_research_only, live_operational_connected=false.
- An optional authenticated, **loopback-only** read API may follow a separate review; release v1 needs no network listener.
- Command wrappers must preserve existing scripts/doug-max guardrail behavior and never add an exemption to executable dispatch or relax the baseline blocklist.

## 11. Integration interfaces

### GPT-Doug (query and reasoning)

- Offline, schema-driven query access to ZYRA base type definitions and the reviewed research overlay.
- Unreviewed experiments must appear only under an explicit include_unreviewed filter; never as a default answer source.
- Retrieval returns provenance, publication status, mathematical/empirical scope and a mandatory RESEARCH_ONLY label.
- The research engine does not use GPT-Doug to autonomously submit tasks or write model weights.

### PINEAL (external memory)

- Read-only retrieval from local PINEAL store for approved, permitted facts when explicitly enabled.
- After approved publication, optionally write minimal research-only namespace triples containing publication ID, claim summary, digest, provenance and review record reference, using the existing store.put API and audit semantics.
- No automatic harvesting of personal memory. PINEAL's current bridge does not automatically read this new research schema; the integration must be added as an opt-in, validated adapter.
- Never write into warfighter-defense-si observations except via its existing synthetic-only allowlist and user-controlled flow. Research output is not a live observation.

### ZYRA / ZYRA-MSS (governance)

- Import **schema and reviewed evidence references**, not operational state updates.
- Existing Glass Onion/HUMAN_APPROVAL_REQUIRED policies and blocked-action categories remain active.
- Propose new machine-verifiable policy gates in a separate extension rather than amending or bypassing canonical ZYRA_MSS_V1:
  - RESEARCH_ISOLATED
  - SOURCE_RIGHTS_VERIFIED
  - SYNTHETIC_WARFIGHTER_DATA_ONLY
  - MODEL_CERTIFICATE_REPLAYED
  - HUMAN_APPROVAL_BOUND_TO_DIGEST
  - RESEARCH_ONLY_PUBLICATION
  - NO_DISPATCH_NO_ACTUATION
  - AUDIT_SINK_AVAILABLE
- Document that a JSON rule/policy name is not itself a deployed authorization enforcement mechanism; each must have a tested enforcement point.

### Future 6D / Blender visual cortex

- May consume sanitized and reviewed or explicitly labeled DEMO snapshots: model name, simulation stage, dimensionality, status, memory count, heartbeat freshness, CPU/RAM telemetry when truly measured.
- The 3D projection has only 3 physical display coordinates; other "dimensions" are encoded as data/time channels. The optional string-inspired viewer may project 10D/11D mathematical objects into 3D without claiming physical higher-dimensional perception.
- No visualizer writes to ontology or review state. Missing data is MISSING/STale, not silently treated as LIVE.
- Optional Blender runtime and its proposed 6D visualization are **not** prerequisites for the v1 research ontology.

## 12. Storage, versioning and lifecycle

- Store immutable simulation request and result pairs, verification envelopes and review records in local, gitignored workspace: for example, \${GPT_DOUG_RESEARCH_HOME:-~/.local/share/gpt-doug-warfighter-research}/, not within repo config files. User-controlled override must resolve to a permitted safe directory.
- Keep schema and golden synthetic fixtures in version control. Never commit private datasets, actual defense data, locally saved review identities or secrets.
- Publication uses an append-only JSONL or SQLite event journal with stable event IDs, checksum, schema version and previous-event digest. SQLite transactions provide atomic local commits, not global distributed transactions.
- Rebuild overlay indexes from approved publication events on startup. The canonical schema and study results are different authorities; experimental storage cannot become source of truth for mission operations.
- Retention: default synthetic runs retained locally until manual removal; after revocation, maintain minimal audit tombstones and purge mutable projections. A future regulated retention policy must be approved separately.
- Schema evolution: semantic versioning, migration tests and compatibility matrix; forward major-version changes require explicit review. Existing ZYRA_MSS_V1 remains unchanged.
- All exports include source and claim labels, manifest hashes, known limitations, deterministic replay identifiers and schema versions.

## 13. Security/privacy and threat model

**Threats:** prompt-/data-injection masquerading as ontology metadata; malicious local file paths or symlinks; fake public-source labels; out-of-memory numerical cases; corrupted or replaced certificates; forged "APPROVED" fields; replay of revoked findings; disclosure of sensitive telemetry; unsafe existing XQE task-dispatch integration; inference that synthetic metrics measure actual military posture.

**Mitigations:**

- Strict JSON schemas, allowlisted object/edge/metric names, bounded string length, file-size and numeric magnitude limits, canonical byte hashing, explicit provenance and source-rights checks.
- Reject code, embedded instructions, arbitrary URLs, filesystem escapes, traversal/symlink paths, credential-looking fields and unsupported data classification.
- No network access or external connectors during simulation. Separate opt-in public-source reference ingestion would require its own approval and legal/security review.
- Restrict filesystem access to designated workspace; output files created with private permissions; no blind directory scans.
- Deterministic CPU/time/memory ceilings; terminate only this subsystem's owned child process if limits are exceeded, not the operator's heartbeat or system services.
- Never call XQE.verify/run (dispatching), weapons functions, real drone/vehicle control, targeting pipelines, exploit tools, live sensor endpoints or arbitrary shell commands from the new research runtime.
- Review state is bound to exact digest; an external caller cannot set status APPROVED merely by writing a JSON field without a matching locally recorded review transaction.
- Truthful display of failed checks, stale observations, unsupported source types, missing attestations and partially projected publications.
- Preserve the ZYRA_MSS_V1 blocked-action set in every path, including terminal, API and dashboard.

**Human authority:** Approval authorizes publication of a *research finding*, not any real-world action. No operational task or security control can be modified via the review/publish operation.

## 14. Nonfunctional budgets and accessibility

For the first offline iteration on an Apple Silicon laptop with ~8 GiB RAM:

- Standard-library-first baseline and Bio-Hilbert reuse; no paid token or cloud service requirement.
- Engine B must obey *existing* 128-mode / 8-step caps and exact rational bit-size limits. Do not raise caps without profiling and mathematical review.
- Engine C initial maximum: 6 simulated qubits, 128 declared gate operations, 1024 sampled measurements (if sampling is enabled), default 30-second task deadline. These are engineering proposal caps, not claims of existing implementation.
- Engine D initial maximum: 11 ambient dimensions, 256 sample points per toy object, 1000 projected vertices and deterministic projections; rendering is optional.
- Scenario JSON <=64 KiB, output manifest <=1 MiB, max 100 typed graph objects and 500 relationships per sample, max 20 local queued synthetic runs, concurrency default 1.
- Fail early with RESOURCE_LIMIT_REACHED rather than allocating unbounded matrices or exact fractions.
- Headless terminal and JSON work without Blender, GPU, model API, subscription or local LLM installation.
- All major statuses have readable text (not color alone), screen-reader-friendly JSON/summaries and finite frame options if animation is added.
- On missed deadline, show TIMEOUT with no claim of proof or success. Store the failed run's metadata without publication.

## 15. Proposed repository layout (not created by this spec)

~~~text
docs/superpowers/specs/2026-10-12-quantum-warfighter-ontology-design.md
docs/WARFIGHTER_RESEARCH_ONTOLOGY.md
safety-shield/ontology/warfighter-research-v1.json
research_lab/warfighter/
    __init__.py
    schema.py                    # strict declarative validation
    domain.py                    # typed synthetic graph and relations
    fixtures.py                  # bounded synthetic scenario input
    baseline.py                  # nonoperational deterministic comparator
    hilbert_adapter.py           # pure adapter to existing math engine
    quantum_inspired.py          # optional classical statevector
    geometry_nd.py               # optional higher-D projection
    verify.py                    # independent replay and certificate checks
    review.py                    # explicit local human decision workflow
    publication.py               # event log and read-only overlay projection
    cli.py                       # proposed command group
research_lab/warfighter/examples/
    synthetic_training_defense.json
research_lab/warfighter/tests/
    test_schema.py
    test_models.py
    test_certificates.py
    test_policy.py
    test_review_publication.py
    test_cli_e2e.py
~~~

Existing integration adapters will be added only after isolated modules and tests succeed. The above are **future implementation targets**, not files currently claimed to be present.

## 16. Failure semantics, rollback and recovery

| Failure | Required response |
| --- | --- |
| Missing/malformed scenario, unauthorized classification | Reject before computation; no writes to overlay |
| Oversized input, mode/step/qubit cap exceeded | RESOURCE_LIMIT_REACHED; no partial publish |
| Certificate mismatch or numerical check fails | verification FAILED; keep in quarantine; no review approval route |
| Review references different digest/version | CONFLICT; require new review |
| Audit event cannot be committed | fail closed and return NOT_PUBLISHED |
| PINEAL unavailable | keep reviewed journal truth; report PINEAL_NOT_PROJECTED; retry only via explicit idempotent operation |
| Revocation after publication | append revocation; hide from current retrieval; mark any projections stale/revoked; preserve minimal audit trail |
| Blender absent, GPU unmeasured | terminal/JSON continue; never advertise live GPU or 3D functionality |
| Existing heartbeat stale/missing | label STALE/MISSING; never infer research or operational readiness |

Rollback procedure: disable the new read-only overlay adapter and wrapper command, preserve underlying source artifacts for audit, restore previous schema/router registration. Since base ZYRA_MSS_V1 is unchanged, rollback must not require data repair to mission-support records.

## 17. Test plan and release acceptance matrix

1. **Schema tests:** 20+ positive/negative object/edge fixtures, unknown fields, missing required fields, wrong endpoints, duplicate IDs, orphaned evidence, cyclic self-approval, disallowed classifications.
2. **Rights and data-boundary tests:** reject CUI/SECRET, real warfighter feeds, precise geolocation, personal/medical data, credentials, fabricated PUBLIC labels and non-synthetic warfighter-defense-si writes.
3. **Baseline model tests:** deterministic replay with canonical sorting, explicit formulas, artificial sample changes, no ambiguous aggregate readiness claims.
4. **Bio-Hilbert compatibility:** existing exact-rational sample and stability certificate pass with same digests; failure with invalid h, modes, steps or violated assumptions; source code untouched.
5. **Quantum-inspired tests:** normalize state vectors, unitary action, probability sums within stated tolerance, deterministic sampling seed, cap rejection, no quantum-hardware claims.
6. **Higher-D geometry tests:** declared dimension 6/10/11, correctly sized projection matrices, finite coordinates, deterministic mesh sampling, noninvertible projection warning.
7. **Review/publish tests:** cannot publish unverified or unapproved data; cannot spoof review using JSON edit; exact digest binding; denied operator action; publication idempotence; revocation/tombstone; no changes to ZYRA_MSS_V1.
8. **PINEAL integration tests:** synthetic-only metric policy unchanged; namespace-only promotion; no writes during run/verify/query/visualize; append-only memory audit semantics preserved; PINEAL outage retry is accurate.
9. **XQE containment:** test import graph and monkeypatched dispatch functions to prove research commands never call workers.xqe.run/verify or ontology.submit_task_action.
10. **Repository regressions:** existing research_lab, ZYRA-MSS doctor and PINEAL federation/bridge/store tests pass under supported Python versions.
11. **Operator UX:** JSON/terminal status distinguishes proposed vs implemented, simulation vs live, verified math vs reviewed claim, research-only vs operational; Ctrl-C cleans up owned processes.
12. **Security negatives:** path traversal, symlink escapes, huge fractions/complex matrices, malformed JSON, hash collisions simulated via mismatched digest checks, and deterministic resource-ceiling behavior.

**V1 acceptance gate:** all above applicable tests pass; a local synthetic scenario moves through simulated -> independently verified -> explicitly approved -> published into *research overlay only*; the same scenario without reviewer authorization remains unpublished; PINEAL projection is optional and truthful; no actual operational readiness data or external system interaction occurs.

Optional mathematical/visual engines (C/D) have separate milestones and cannot block the safe baseline if unavailable. Neither a simulation test nor a mathematical proof alone establishes military suitability.

## 18. Milestone order and planned files

**M0 — foundations (first implementation plan):** typed v1 research schema, fixture loader, provenance policy, deterministic baseline, read-only inspect CLI and tests. No PINEAL write; no new background service.

**M1 — verified mathematical simulations:** adapt existing Bio-Hilbert and exact multidimensional certificates, implement research run artifacts + verifier + tests, retain strict limit caps.

**M2 — human-reviewed ontology promotion:** local review/audit journal, immutable research overlay, PINEAL projection with opt-in manual publication and reconciliation; verify no ZYRA authority mutation.

**M3 — quantum-inspired and string-inspired labs:** small classical statevector and 10D/11D visualization, separately validated, explicitly experimental, no new user permissions or operational connection.

**M4 — ergonomic visualization:** optional bridge to separately approved PINEAL 6D/Blender view; terminal-first, read-only, graceful fallback.

**M5 — independent hardening:** security audit, resource profiling, reproducibility reviews, documentation, release signing options. Any future real/regulated data integration requires a new scoped security design and explicit authorization, not a flag in this prototype.

## 19. Review checklist and final architectural constraints

Reviewers should confirm:

- [ ] One base authority: ZYRA_MSS_V1 remains unchanged and authoritative.
- [ ] Synthetic Warfighter and authorized public *reference* data only; no live operational defense data.
- [ ] Research engine runs offline, with limits and no task dispatch or external effects.
- [ ] Quantum-inspired classical simulation and higher-dimensional projections are labeled accurately.
- [ ] MathCertificate verifies the stated formal model, not real-world effectiveness.
- [ ] Human decision is necessary for publication and bound to exact artifact hash.
- [ ] Only reviewed results enter versioned *research overlay*; none enter readiness authority.
- [ ] Optional PINEAL writes use a dedicated research namespace and an explicit operator action.
- [ ] All changes are backward-compatible, testable, reversible and run without paid tokens.
- [ ] No weapons, targeting, operational tracking, external command or unapproved data access.

### Nonnegotiable design invariants

I1. **No research-to-operational authority edge.**  
I2. **No unreviewed result in default ontology retrieval.**  
I3. **No mathematical result promoted beyond its assumptions or proof.**  
I4. **No Warfighter observation without SYNTHETIC classification and allowlisted metric.**  
I5. **No autonomy, external dispatch, real-world actuator, scanning or targeting.**  
I6. **Every published finding has immutable provenance, replay verification and a human decision reference.**  
I7. **No inference of DoD status, system certification, 6D physical implementation, quantum advantage or actual string-theory validation.**

---

**Approval gate:** This file is the complete **architectural specification**, not an implementation plan or code. The user should review/approve this written artifact before a separate implementation plan is prepared. That plan must identify exact commits, tests, execution method, and the first testable M0/M1 slice. Do not treat approval of the earlier high-level approach as approval to begin implementation.
