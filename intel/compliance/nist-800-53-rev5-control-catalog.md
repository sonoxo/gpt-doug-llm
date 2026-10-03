# NIST SP 800-53 Rev. 5 Control Catalog Mapping

## Purpose
This artifact maps GPT-DOUG-LLM / ZYRA compliance evidence to the NIST SP 800-53 Revision 5 security and privacy control catalog.

This is an **evidence and readiness mapping**, not a certification, authorization, ATO, FedRAMP authorization, CJIS acceptance, FIPS validation, or other external approval.

## Source hierarchy
1. **Authoritative control catalog:** NIST SP 800-53 Rev. 5, Security and Privacy Controls for Information Systems and Organizations.
2. **Assessment methodology:** NIST SP 800-53A Rev. 5.
3. **Baseline selection:** NIST SP 800-53B.
4. **Operator UI reference:** compliance.gov EdgeScan → Controls Catalog → NIST SP 800-53 Rev. 5, supplied to the project on 2026-09-06 as a visual reference for control-catalog presentation.

The operator UI reference does not replace NIST as the authoritative control source.

## Catalog families
NIST Rev. 5 organizes security and privacy controls into 20 families:

| ID | Family | GPT-DOUG evidence focus |
|---|---|---|
| AC | Access Control | bounded agent permissions, tool authorization, least privilege, access plans |
| AT | Awareness and Training | operator/developer security training evidence |
| AU | Audit and Accountability | audit logging, traceability, tamper-evidence, event review |
| CA | Assessment, Authorization and Monitoring | CI/security gates, assessment evidence, monitoring, authorization boundaries |
| CM | Configuration Management | version control, approved configuration, change control, drift prevention |
| CP | Contingency Planning | backup, recovery, continuity, restoration procedures |
| IA | Identification and Authentication | runtime identities, authentication strength, service identities |
| IR | Incident Response | preparation, detection, containment, eradication, recovery, lessons learned |
| MA | Maintenance | controlled maintenance, authorized tooling, maintenance records |
| MP | Media Protection | regulated data/media handling when applicable |
| PE | Physical and Environmental Protection | deployment-site physical controls when applicable |
| PL | Planning | system security plan, rules of behavior, architecture and boundary planning |
| PM | Program Management | governance, risk ownership, compliance command structure |
| PS | Personnel Security | personnel screening, role assignment, termination/transfer controls |
| PT | PII Processing and Transparency | privacy scope, PII processing, transparency and consent requirements |
| RA | Risk Assessment | vulnerability analysis, threat intelligence, POA&M and risk treatment |
| SA | System and Services Acquisition | SDLC, dependency governance, supplier requirements, SBOM |
| SC | System and Communications Protection | network boundaries, cryptography, secure communications, isolation |
| SI | System and Information Integrity | flaw remediation, malware protection, monitoring, integrity validation |
| SR | Supply Chain Risk Management | supplier provenance, dependency risk, service/provider assurance |

## Evidence-state model
Every mapped control or family must resolve to one of these repository states:

- `IMPLEMENTED_EVIDENCE_PRESENT` — implementation evidence exists in source-controlled artifacts.
- `PARTIAL_EVIDENCE` — some implementation evidence exists, but additional technical or operational evidence is required.
- `DEPLOYMENT_EVIDENCE_REQUIRED` — correctness depends on the deployed environment or organization and cannot be proven by repository code alone.
- `EXTERNAL_AUTHORIZATION_REQUIRED` — an external assessor, authority, or authorization decision is required.
- `NOT_APPLICABLE_BY_DECLARED_SCOPE` — applicability has been explicitly excluded by the declared system/data scope.
- `SOURCE_GAP` — expected repository evidence is missing.

## Assessment rule
A control is not considered satisfied merely because:

- a matching policy document exists;
- a CI job passes;
- a security scanner reports no findings;
- a dependency is commonly used in regulated environments;
- the control appears in an EdgeScan/compliance.gov catalog UI;
- another system or cloud provider has an authorization.

Assessment must distinguish **implementation**, **operating effectiveness**, **scope**, **inherited controls**, **assessment evidence**, and **authorization status**.

## Baseline rule
SP 800-53 is the catalog. SP 800-53B defines Low, Moderate, High, and Privacy baselines and tailoring guidance. GPT-DOUG-LLM must not imply that every catalog control is automatically required for every deployment.

A deployment-specific baseline decision must document:

1. system boundary;
2. information types and impact;
3. selected baseline or governing overlay;
4. tailoring decisions;
5. inherited controls;
6. implementation evidence;
7. assessment results;
8. residual risks and POA&M entries;
9. authorization/acceptance decision where externally required.

## Control evidence contract
For each control promoted into an audit result, the evidence record SHOULD contain:

```json
{
  "controlId": "AC-2",
  "family": "AC",
  "state": "PARTIAL_EVIDENCE",
  "applicability": "IN_SCOPE",
  "implementationEvidence": [],
  "deploymentEvidence": [],
  "inheritedEvidence": [],
  "assessmentEvidence": [],
  "gaps": [],
  "provenance": [],
  "reviewedAt": null
}
```

## Command doctrine
**Compliance is an evidence state, not a branding claim.**

The Controls Catalog is used to organize evidence, identify gaps, and drive assessment. It must never be used to manufacture a generalized "NIST compliant" claim without naming the applicable control set, scope, evidence state, and any required external authorization.
