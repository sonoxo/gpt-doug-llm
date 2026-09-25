# TECH FORCE // OPEN CALL ORDERS

**Status:** OPEN  
**Issued:** 2026-09-23  
**Program type:** civilian/open-source engineering contributor program  
**Authority boundary:** See [ECOSYSTEM_DISCLAIMER.md](ECOSYSTEM_DISCLAIMER.md)

> **Tech Force is not a military unit or government program. Open Call Orders are scoped engineering work orders, not military orders or authorization to access third-party systems.**

## Mission

Recruit builders who can make the GPT-DOUG / XUNIA ecosystem safer, more observable, more interoperable, more accessible, and easier to verify.

The public contribution surface is defensive and research-oriented: secure software, resilience, simulation, provenance, ontology, testing, compliance, accessibility, documentation, and lawful threat intelligence.

## Operating contract

Every accepted contribution should follow:

`scope -> build -> test -> security check -> evidence -> review -> merge`

For security research:

`owned/authorized target -> isolated test -> reproduce -> document -> mitigate -> verify`

Do not conduct unsanctioned intrusion, persistence, disruption, destructive effects, surveillance, or targeting under the Tech Force name.

---

## OPEN CALL ORDER TF-001 // GOVERNANCE + AUTHORITY GRAPH

**Objective:** Make authority machine-readable across the ecosystem.

**Deliverables:**
- ontology objects for `Authority`, `Approval`, `Scope`, `TargetClass`, `Evidence`, and `Expiration`;
- validation that consequential actions cannot proceed when authority is missing or expired;
- human-readable policy mapping and tests.

**Boundary:** synthetic/example authorizations only in the public repo.

## OPEN CALL ORDER TF-002 // CYBER RANGE + SAFE TARGET LAB

**Objective:** Improve safe hands-on security testing without touching third-party infrastructure.

**Deliverables:**
- containerized intentionally vulnerable test services;
- resettable fixtures and synthetic logs;
- attack/defense exercises limited to the local range;
- deterministic cleanup and evidence capture.

**Boundary:** localhost, containers, VMs, owned systems, or explicitly authorized lab targets only.

## OPEN CALL ORDER TF-003 // DEFENSIVE THREAT-INTEL PIPELINE

**Objective:** Normalize lawful public/authorized security intelligence into the shared ontology.

**Deliverables:**
- adapters for public advisories and vulnerability feeds;
- source provenance, timestamps, confidence, and deduplication;
- mapping to defensive detections, mitigations, and patch priorities;
- tests using fixtures rather than live intrusive collection.

**Boundary:** no credential theft, covert collection, or unauthorized surveillance.

## OPEN CALL ORDER TF-004 // RESILIENCE DIGITAL TWIN

**Objective:** Model service dependencies and failure recovery before real changes are made.

**Deliverables:**
- typed service/dependency graph;
- synthetic outage and degradation scenarios;
- recovery recommendations with confidence and rollback plans;
- dry-run/simulation mode as the default.

**Boundary:** no autonomous control of public utilities, transportation, emergency services, or other third-party critical infrastructure.

## OPEN CALL ORDER TF-005 // COMPLIANCE + CONTROL MAPPING

**Objective:** Turn security requirements into verifiable engineering checks.

**Deliverables:**
- mappings to relevant NIST/CISA/contractual controls where appropriate;
- repository checks that point to evidence rather than self-attestation;
- control ownership and exception tracking;
- beginner-readable explanations.

**Boundary:** mappings do not claim certification, accreditation, clearance, or government approval.

## OPEN CALL ORDER TF-006 // AUDIT + PROOF ENGINE

**Objective:** Make “done” mean verifiably done.

**Deliverables:**
- append-only or tamper-evident execution evidence where practical;
- test/build/deploy proof summaries;
- commit, CI, artifact, and rollback references;
- failure states that clearly distinguish configured, attempted, verified, and deployed.

## OPEN CALL ORDER TF-007 // ACCESSIBILITY + BEGINNER OPS

**Objective:** Reduce cognitive load for operators and contributors.

**Deliverables:**
- one-command workflows;
- accessible terminal/web guidance;
- large-state/status indicators;
- plain-language runbooks and recovery steps;
- safeguards against accidental consequential actions.

## OPEN CALL ORDER TF-008 // SOFTWARE SUPPLY-CHAIN DEFENSE

**Objective:** Harden dependencies, builds, releases, and deployment paths.

**Deliverables:**
- dependency and secret scanning;
- provenance/SBOM improvements;
- least-privilege CI permissions;
- release verification and rollback documentation;
- tests that fail closed on missing integrity evidence.

## OPEN CALL ORDER TF-009 // NSS GOVERNANCE MAPPING

**Objective:** Map public National Security Systems governance concepts into the ecosystem without implying government status.

**Deliverables:**
- ontology objects for `NSS`, `CNSS`, `NationalManager`, `GovernanceRole`, and `AuthorityBoundary`;
- public-source provenance and date tracking;
- tests preventing claims of NSS access, designation, CNSS membership, clearance, or Federal authorization.

**Boundary:** public-policy mapping only; no NSS access, credentials, or operational integration.

## OPEN CALL ORDER TF-010 // VULNERABILITY COORDINATION LAB

**Objective:** Build a defensive vulnerability intake, triage, provenance, prioritization, disclosure, and remediation workflow modeled on public Federal coordination concepts.

**Deliverables:**
- local vulnerability intake schema;
- provenance and severity tracking;
- remediation evidence and disclosure workflow;
- synthetic fixtures and authorized test targets.

**Boundary:** no unsanctioned scanning, exploit deployment, third-party remediation, or access to Federal vulnerability feeds.

## OPEN CALL ORDER TF-011 // CMMC / NIST 800-171 EVIDENCE LAB

**Objective:** Build non-authoritative security evidence and control-mapping tooling for future defense-supply-chain readiness.

**Deliverables:**
- asset inventory and control-evidence mappings;
- access-control, audit, configuration, incident, and supply-chain evidence workflows;
- explicit distinction between local evidence and an actual assessment.

**Boundary:** no claim of CMMC certification, assessment, DIB approval, contract eligibility, or government acceptance.

## OPEN CALL ORDER TF-012 // POST-QUANTUM CRYPTOGRAPHY MIGRATION LAB

**Objective:** Prepare ecosystem software for cryptographic agility and future PQC migration.

**Deliverables:**
- local cryptographic dependency inventory;
- identification of key-establishment and digital-signature dependencies;
- algorithm-agility and migration/rollback tests;
- cryptographic bill-of-materials experiments;
- migration-readiness evidence.

**Boundary:** owned/local/synthetic systems only. Do not collect third-party keys, decrypt protected third-party traffic, or test Federal/NSS/critical-infrastructure systems without explicit authorization. EO 14412 and OMB M-26-15 are public policy references, not project authorization.

## OPEN CALL ORDER TF-013 // HUMAN-CONTROLLED AI ASSURANCE LAB

**Objective:** Test AI security, controllability, auditability, approval gates, rollback, and safe simulation patterns.

**Deliverables:**
- model/system evaluation harnesses;
- human approval gates for consequential actions;
- audit and provenance records;
- fail-closed behavior and rollback tests;
- synthetic mission and cyber-range scenarios.

**Boundary:** no weapons targeting, autonomous lethal action, mission-system access, or DoD authorization claims.

---

## Who should answer the call

Useful backgrounds include Python, TypeScript, Rust/Go, DevSecOps, cloud engineering, ontology/data modeling, threat intelligence, reverse engineering in isolated labs, AI/ML evaluation, compliance, UX/accessibility, technical writing, testing, and reproducible infrastructure.

Beginners are welcome when the task is appropriately scoped. A small verified pull request is more valuable than a large unverified claim.

## How to join

1. Read [ECOSYSTEM_DISCLAIMER.md](ECOSYSTEM_DISCLAIMER.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
2. Pick one Open Call Order above.
3. Open or claim a narrowly scoped GitHub issue describing the deliverable and proof method.
4. Build on a branch/fork.
5. Submit a focused pull request with tests, evidence, and limitations.
6. Let CI and reviewer verification determine acceptance.

Accepted work receives normal Git/GitHub attribution. Participation does not create employment, government status, military status, clearance, procurement eligibility, or operational authority.

## Government-program readiness lane

Contributors may help build **non-operational readiness artifacts** such as compliance mappings, evaluation harnesses, cyber-range simulations, proposal-support documentation, authorization schemas, audit tooling, PQC migration planning, and defensive prototypes.

If an actual government-directed cyber program or contract later becomes applicable, operational participation must remain disabled until the specific legal, contractual, vetting, oversight, approval, and target-scope requirements are independently satisfied.

---

**CALL SIGN:** BUILD SAFE. PROVE IT. KEEP AUTHORITY EXPLICIT.
