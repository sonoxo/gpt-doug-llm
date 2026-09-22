# GPT-DOUG / GPT-CHAOS Learning Ingestion
## SEI Software Assurance + Adaptive Acquisition Framework
Date: 2026-09-21

## Sources

1. Carnegie Mellon University Software Engineering Institute, *DoD Developer's Guidebook for Software Assurance*, CMU/SEI-2018-SR-013, December 2018.
   - Source URL: https://www.sei.cmu.edu/documents/1949/2018_003_001_538761.pdf
   - Verified alternate SEI publication endpoint: https://www.sei.cmu.edu/library/file_redirect/2018_003_001_538761.pdf/
   - Evidence depth: FULL_TEXT_VERIFIED
   - Publication status: public release / unlimited distribution.
   - Important provenance rule: the report states that its findings should not be construed as official Government policy unless separately designated.

2. WarU / DAU, *Adaptive Acquisition Framework (AAF) Quick Reference Card*, user-supplied URL for v3.8, 13 April 2026.
   - Source URL: https://www.waru.edu/sites/default/files/2026-04/DoD%20AAF%20Quick%20Ref%20--v.3.8%2C%2013%20April%202026.pdf
   - Evidence depth for exact v3.8 PDF: URL_CONFIRMED_BY_USER_BUT_FETCH_BLOCKED
   - Official WarU/DAU public pages and the accessible v3.6 quick-reference search index corroborate the stable AAF concepts below.
   - Version-specific thresholds, wording, and deltas unique to v3.8 are NOT promoted until the exact PDF is retrievable.

## Canonical doctrine

```text
MISSION CONTEXT
   -> PATH / LIFECYCLE SELECTION
   -> REQUIREMENTS + THREAT MODEL
   -> SECURITY / ASSURANCE PLAN
   -> BUILD / ACQUIRE
   -> STATIC + DYNAMIC + NEGATIVE TESTING
   -> PROVENANCE / SUPPLY-CHAIN CHECKS
   -> VERIFY + VALIDATE
   -> MEASURE AGAINST MISSION GOALS
   -> HUMAN DECISION / ACCEPTANCE
   -> DEPLOY / TRANSITION
   -> MONITOR + SUSTAIN + EVOLVE THREAT MODEL
   -> RECOVER / ROLLBACK
```

## GPT-DOUG - promoted learning

### 1. Mission-first software assurance
Software assurance is not a generic checklist. Security decisions should be driven by operational/mission context, expected threats, mission impact, lifecycle stage, and system dependencies.

Project rule:
- Every consequential software mission MUST declare a mission objective, operational context, critical dependencies, and expected failure impact.
- Threat and assurance work MUST be traceable to mission relevance.

### 2. Secure-by-lifecycle, not "security at the end"
Assurance spans requirements, architecture, implementation, integration, verification, transition, validation, operation, maintenance, and acquisition/sustainment.

Project rule:
- Security controls, tests, provenance, and assurance evidence are lifecycle objects.
- A deployment gate cannot substitute for missing earlier requirements or design assurance.

### 3. Fail-safe defaults, complete mediation, least privilege
The SEI guidebook reinforces classic protection principles:
- simple mechanisms,
- permission-based defaults,
- every access checked,
- open design rather than security by obscurity,
- separation of privilege,
- least privilege,
- minimal shared mechanisms,
- usable security controls.

Project rule:
- Unknown or unregistered tool/action = DENY or REQUIRE_REVIEW.
- Capability grants are explicit, scoped, revocable, and auditable.

### 4. Goal -> Question -> Metric
Measures should answer decisions, not exist for decoration.

Project rule:
- Every promoted assurance metric records:
  - goal,
  - decision question,
  - measurement,
  - interpretation,
  - validation/limitations.
- Avoid "metric theater": counts alone do not prove effectiveness.

### 5. Layered analysis
No single analysis method is sufficient. Static, dynamic, hybrid, manual, provenance/origin, negative testing, fuzzing, coverage, signatures, and other methods cover different objectives.

Project rule:
- GPT-DOUG may recommend layered evidence suites based on context.
- Tool choice MUST be justified against mission risk, component type, lifecycle stage, language/runtime, supply-chain exposure, and operational usage.

### 6. Supply-chain provenance
Third-party, COTS, GOTS, OSS, libraries, binaries, build inputs, and delivered components require provenance and vulnerability awareness.

Project rule:
- Material software artifacts require origin/provenance fields.
- Unknown provenance, unresolved known vulnerabilities, or unverifiable component origin trigger GPT-CHAOS review and may block promotion.

### 7. Risk = likelihood + consequence, interpreted in mission context
Not all findings have identical urgency. Risk must account for exploitability/likelihood and severity/consequence, including mission effect.

Project rule:
- Findings carry severity, exploitability, mission impact, remediation cost, uncertainty, owner, disposition, and residual risk.
- Low-cost fixes may be handled directly; consequential tradeoffs require human review.

### 8. Sustainment is continuing development
The threat model, codebase, components, hardware, operational environment, and staff change over time.

Project rule:
- Preserve architectural decisions and reasons, not only code.
- Continue assurance tooling into sustainment where practical.
- Continuously identify, detect, respond, resist, and recover.
- Re-open risk when dependencies, environment, mission, or threat model materially changes.

### 9. Objective acceptance and negative testing
Acquirers and builders can define objectively verifiable acceptance criteria and negative tests rather than relying on confidence statements.

Project rule:
- Every high-risk software capability should have negative/adversarial tests plus explicit pass/fail criteria before promotion.

## GPT-CHAOS - promoted critic behavior

GPT-CHAOS MUST ask:

1. What mission outcome could fail?
2. What threats or misuse cases were omitted?
3. Which dependencies are being trusted without evidence?
4. Is this tool/evaluator appropriate for this lifecycle stage and component context?
5. Are static, dynamic, negative, origin, or manual checks missing?
6. Are security metrics tied to a decision or merely counts?
7. Are supply-chain components and provenance known?
8. What is the likelihood AND mission consequence of the finding?
9. Is residual risk documented and owned by a human authority?
10. Has the threat model changed since the last release?
11. Can the system detect, resist, recover, and roll back?
12. Are acceptance criteria objectively testable?

GPT-CHAOS does not self-authorize exceptions.

## AAF learning model

Official WarU/DAU public materials corroborate six AAF pathways:

- Urgent Capability Acquisition (UCA)
- Middle Tier of Acquisition (MTA)
- Major Capability Acquisition (MCA)
- Software Acquisition Pathway (SWP)
- Defense Business Systems (DBS)
- Acquisition of Services (SA)

Promoted architecture lessons:

### Tailoring
Program strategy, reviews, documentation, and decision detail should be tailored to the capability and risk rather than driven by one universal checklist.

GPT-DOUG mapping:
- missions carry a `delivery_path` / `governance_path` field;
- required evidence is path- and risk-dependent;
- controls cannot be waived merely because a faster path is selected.

### Multiple pathways
Programs may need more than one pathway, with explicit transition points and information handoffs.

GPT-DOUG mapping:
- transitions are first-class ontology events;
- transition requires source/target path, decision authority, entry criteria, required information, unresolved risks, and approval.

### Cybersecurity early and continuous
Cybersecurity is treated as a lifecycle concern rather than a final inspection.

GPT-DOUG mapping:
- security gates begin at mission definition and persist through sustainment.

### Software Acquisition Pathway
Software delivery favors rapid iteration and frequent capability delivery.

GPT-DOUG mapping:
- use bounded iterations, MVP/MVCR-style checkpoints, versioned releases, explicit acceptance evidence, and continuous feedback;
- speed NEVER bypasses safety, provenance, policy, or human approval for consequential effects.

## Acquisition ontology additions

```text
AcquisitionMission
AcquisitionPathway
DecisionAuthority
TransitionPoint
InformationRequirement
StatutoryRequirement
RegulatoryRequirement
SecurityRequirement
AssurancePlan
ProgramProtectionArtifact
SoftwareComponent
SupplyChainEvidence
VerificationEvidence
ValidationEvidence
NegativeTest
MetricDefinition
RiskFinding
ResidualRisk
SustainmentEvent
ThreatModelVersion
RecoveryPlan
```

## Non-claims and boundaries

- The 2018 SEI report is a technical guidebook, not automatically current policy.
- The exact 2026 v3.8 AAF PDF could not be retrieved by the current crawler; do not fabricate its unique wording, thresholds, or changes.
- Current policy status must be checked against authoritative DoD/WarU/DAU sources before making compliance claims.
- Learning here changes the GPT-DOUG/GPT-CHAOS project ontology and design doctrine; it does not alter hidden model weights.
- "Learn" means source-grounded, versioned, testable project memory - not silent self-modification.
