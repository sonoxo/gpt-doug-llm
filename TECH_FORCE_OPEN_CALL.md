# TECH FORCE // OPEN CALL ORDERS

**Status:** OPEN  
**Issued:** 2026-09-07  
**Program type:** Civilian/open-source engineering contributor program  
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

Contributors may help build **non-operational readiness artifacts** such as compliance mappings, evaluation harnesses, cyber-range simulations, proposal-support documentation, authorization schemas, audit tooling, and defensive prototypes.

If an actual government-directed cyber program or contract later becomes applicable, operational participation must remain disabled until the specific legal, contractual, vetting, oversight, approval, and target-scope requirements are independently satisfied.

---

**CALL SIGN:** BUILD SAFE. PROVE IT. KEEP AUTHORITY EXPLICIT.