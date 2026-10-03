# GUARDIAN Active Defense Blueprint

## Purpose

GUARDIAN is a defensive, human-governed cyber response subsystem for GPT-Doug-LLM, ZYRA, XUNIA, and Safety Shield. It converts trusted security telemetry into evidence-backed recommendations, simulations, containment actions on locally governed assets, and recovery workflows.

"Retaliation" in GUARDIAN means a defensive response inside an explicitly authorized boundary. It does not mean counter-intrusion into an attacker-controlled system. GUARDIAN must never autonomously deploy malware, steal credentials, exploit third-party systems, launch denial-of-service activity, destroy remote data, or otherwise act outside the protected environment.

## Public references

GUARDIAN may use public patents and demonstrations as architecture inspiration without assuming affiliation, endorsement, license, or implementation rights.

- US 12,722,816 B2: high-level inspiration for a distributed guardian/sensor model in which observations are converted into wearer/operator alerts and protective decisions.
- US 12,680,771 B1: high-level inspiration limited to modularity, reversible interfaces, component isolation, and controlled reconfiguration. Firearm construction, conversion, targeting, and weapon-operating details are outside GUARDIAN's scope.

Open-source publication of GUARDIAN code does not grant patent rights. Implementers are responsible for their own patent and licensing review before commercial deployment.

## Design principles

1. **Deny by default.** Unknown identity, provenance, authorization, integrity, or scope fails closed.
2. **Human authority.** Material, external, destructive, or irreversible actions require explicit human approval; external counter-intrusion is prohibited even with approval.
3. **Authorized boundary only.** Actions may affect only resources identified as locally governed or explicitly authorized.
4. **Simulation before mutation.** Consequential actions require a dry run or isolated simulation first.
5. **Rollback first.** Any mutating action must have a verified rollback or recovery path before execution.
6. **Evidence over inference.** Attribution is never assumed. Observations, hypotheses, confidence, and decisions remain distinct.
7. **Append-only evidence.** Every proposal, approval, denial, execution result, and rollback is recorded.
8. **Least privilege.** Connectors and service identities receive the smallest scope needed for the defensive action.
9. **Privacy by design.** Precise human location, biometrics, and personal telemetry are opt-in, minimized, access-controlled, and excluded from public XUNIA exports by default.
10. **No literal "bulletproof" claim.** GUARDIAN provides defense-in-depth software support; it does not certify physical protective equipment or guarantee invulnerability.

## State model

| State | Meaning | Allowed behavior |
| --- | --- | --- |
| `GREEN` | Verified, scoped, within policy | Observe, correlate, recommend |
| `AMBER` | Elevated uncertainty or impact | Increase telemetry, simulate, require review for material actions |
| `RED` | Confirmed compromise or critical defensive condition | Quarantine owned assets, revoke owned credentials/tokens, block locally governed indicators, preserve evidence, initiate recovery |
| `BLACK` | Trust boundary or control plane compromised | Freeze nonessential mutation, isolate affected route, require explicit recovery authorization |

State transitions are evidence-driven and auditable. A model score alone cannot transition the system into an action-bearing state.

## Core domain model

- `GuardianNode`: a protected asset, service, endpoint, workload, or approved wearable/sensor endpoint.
- `SensorObservation`: immutable observation with source, timestamp, provenance, scope, confidence, and evidence hash.
- `AdversaryHypothesis`: non-authoritative hypothesis describing observed TTP patterns without asserting identity.
- `HazardAssessment`: impact/likelihood assessment with supporting observations.
- `GuardianAlert`: operator-facing alert with state, rationale, confidence, and recommended next action.
- `ResponseProposal`: proposed defensive action with target boundary, expected effect, simulation result, rollback plan, and approval requirement.
- `AuthorizationGrant`: explicit approval record binding approver, scope, action, target, and expiration.
- `DefenseReceipt`: immutable outcome record containing the proposal, authorization, execution result, evidence references, and verification result.

## Decision pipeline

```text
OBSERVE
  -> NORMALIZE
  -> VERIFY PROVENANCE
  -> CORRELATE
  -> ASSESS IMPACT
  -> FORM HYPOTHESIS
  -> GENERATE RESPONSE PROPOSAL
  -> SIMULATE
  -> AUTHORIZED-BOUNDARY CHECK
  -> POLICY GATE
  -> HUMAN APPROVAL WHEN REQUIRED
  -> CONTAIN / DENY / DECEIVE / RECOVER
  -> VERIFY RESULT
  -> APPEND EVIDENCE
  -> LEARN FROM RECEIPT
```

## Permitted defensive actions

GUARDIAN may provide adapters for these actions when the target is locally governed or explicitly authorized:

- isolate a managed endpoint or workload;
- revoke or rotate owned credentials, sessions, API keys, or tokens;
- apply firewall, WAF, EDR, IAM, or service-mesh deny rules within the protected environment;
- rate-limit or disable an exposed owned service;
- quarantine suspicious files or processes on managed systems;
- move suspicious input into a sandbox;
- activate honeytokens, honeypots, decoy documents, or other deception assets inside the protected environment;
- sinkhole owned domains or internal names where the operator controls resolution;
- preserve logs, snapshots, hashes, packet metadata, and other incident evidence;
- restore a verified checkpoint and validate the restored service;
- notify operators through approved visual, audio, haptic, or messaging channels.

## Prohibited actions

GUARDIAN must reject:

- exploiting a suspected attacker or third-party system;
- credential harvesting from external systems;
- malware, ransomware, wipers, destructive payloads, or persistence on systems outside the authorized boundary;
- denial-of-service or resource exhaustion against external targets;
- remote data destruction or manipulation on external systems;
- autonomous external counterattack;
- weapon targeting, fire-control, strike selection, or autonomous physical engagement;
- public exposure of precise human location or biometric telemetry.

## Ecosystem integration

### Safety Shield / SHADOW GLASS

SHADOW GLASS is the outer trust boundary. GUARDIAN proposals must carry verified identity, provenance, target scope, confidence, authorization class, and reversible-action metadata before execution can be considered.

### GLASS ONION

GLASS ONION receives the append-only evidence chain for every observation, proposal, authorization decision, execution attempt, result, rollback, and post-change verification.

### ZYRA

ZYRA agents may investigate, correlate, summarize, generate candidate defensive responses, and run simulations. Agents do not receive blanket mutation authority.

### XUNIA

XUNIA receives a privacy-preserving incident layer containing coarse or operator-approved location, timestamp, state, confidence, provenance status, and LIVE/DELAYED/MODELED classification. Attribution remains explicitly marked as hypothesis unless independently verified.

### Guardian wearable/sensor concept

Optional approved endpoints may report health/status, tamper state, environmental hazards, or operator-defined safety telemetry. GUARDIAN converts these inputs into alerts and check-in workflows. Physical PPE ratings, medical interpretation, and life-critical device control remain outside the autonomous software decision path.

## Open-source boundary

The open-source distribution contains schemas, policy gates, deterministic validators, local simulator adapters, evidence formats, test fixtures, XUNIA export formats, and safe reference adapters. Mutating connectors are disabled by default and require operator-supplied authorization configuration.

## Acceptance criteria

GUARDIAN is ready for merge when:

- every response proposal is boundary-checked and policy-gated;
- unauthorized or unknown targets fail closed;
- external counter-intrusion actions cannot be represented as executable actions;
- RED/BLACK actions require evidence and human authorization according to policy;
- simulation precedes consequential mutation;
- rollback metadata is mandatory for mutating actions;
- append-only receipts cover approvals, denials, executions, and recovery;
- XUNIA export suppresses precise personal location by default;
- deterministic validators and unit tests pass in CI;
- documentation clearly distinguishes defensive active response from offensive counterattack.
