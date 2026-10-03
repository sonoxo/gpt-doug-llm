# ZYRA Government Intelligence System Security Plan

## Command status
This SSP is a living evidence artifact for Virginia and federal intelligence readiness. It does not itself confer authorization, certification, acceptance, or authority to process regulated government data.

## System boundary
- System: GPT-DOUG-LLM / ZYRA / GPT-GLASSONION
- Primary mode: local-first bounded agentic intelligence processing
- External network use: allowlisted read-only public intelligence feeds in dedicated live-sync paths
- High-impact external action: disabled by command doctrine
- Base ontology: provenance locked and hash verified before query
- Intelligence promotion: Virginia Intelligence Command Gate requires source, class, jurisdiction, and provenance locator

## NIST SP 800-53 Rev. 5 control-selection model
- Current reference release: **5.2.0**
- Catalog: NIST SP 800-53 Rev. 5
- Baselines/profile selection: NIST SP 800-53B — Low, Moderate, High, and Privacy
- Assessment procedures: NIST SP 800-53A Rev. 5
- Repository catalog mapping: `intel/compliance/nist-800-53-rev5-control-catalog.md`
- Repository profile model: `intel/compliance/nist-800-53-rev5-profiles.json`
- Operator UI reference: compliance.gov EdgeScan Controls Catalog / Profile Controls screenshots supplied 2026-09-06

The operator UI is a presentation and workflow reference only. NIST publications and current NIST reference data remain authoritative. A profile is not selected from a screenshot; deployment categorization, applicable requirements, tailoring, inherited controls, and privacy scope determine the selected control set.

## Control-family implementation map
| Family | Current command evidence | State |
|---|---|---|
| AC | bounded agent actions; no arbitrary shell in agent core; access-control plan | PARTIAL_EVIDENCE |
| AT | policy artifacts exist; workforce training evidence is deployment-specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| AU | tamper-evident local audit trail documented in SECURITY.md; CI evidence | PARTIAL_EVIDENCE |
| CA | security gate, tests, lint, Bandit, dependency audit, SBOM generation | IMPLEMENTED_EVIDENCE_PRESENT |
| CM | configuration-management plan + git change history + CI | PARTIAL_EVIDENCE |
| CP | contingency plan | PARTIAL_EVIDENCE |
| IA | runtime identity architecture remains deployment-specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| IR | incident-response plan | PARTIAL_EVIDENCE |
| MA | maintenance handled through controlled repository changes; deployment procedures required | DEPLOYMENT_EVIDENCE_REQUIRED |
| MP | regulated-media handling is scope dependent | DEPLOYMENT_EVIDENCE_REQUIRED |
| PE | physical controls are deployment/environment specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| PL | SSP and command doctrine | PARTIAL_EVIDENCE |
| PM | Virginia Intelligence Command framework and compliance fleet | PARTIAL_EVIDENCE |
| PS | personnel screening/role evidence is organization specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| PT | data classification and privacy implementation is use-case specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| RA | security scanning plus POA&M framework | PARTIAL_EVIDENCE |
| SA | dependency audit, SBOM, bounded agent design; Release 5.2.0 update/patch controls require explicit evidence | PARTIAL_EVIDENCE |
| SC | local-first architecture; crypto plan; validated crypto remains environment specific | DEPLOYMENT_EVIDENCE_REQUIRED |
| SI | CI testing, Bandit, dependency audit, live intelligence feeds; Release 5.2.0 update/patch integrity controls require explicit evidence | PARTIAL_EVIDENCE |
| SR | SBOM generation; supplier/service evidence remains environment specific | PARTIAL_EVIDENCE |

## Evidence-state semantics
- `IMPLEMENTED_EVIDENCE_PRESENT`: source-controlled implementation evidence exists.
- `PARTIAL_EVIDENCE`: some evidence exists, with technical or operational gaps.
- `DEPLOYMENT_EVIDENCE_REQUIRED`: repository code cannot prove the deployment-specific requirement.
- `EXTERNAL_AUTHORIZATION_REQUIRED`: an external assessor/authority decision is required.
- `NOT_APPLICABLE_BY_DECLARED_SCOPE`: exclusion is supported by declared system/data scope.
- `SOURCE_GAP`: expected repository evidence is missing.

Implementation, operating effectiveness, assessment results, inherited controls, and authorization status are separate evidence dimensions.

## Conditional command baselines
- Virginia SEC530: applicable when deployed within Commonwealth scope.
- Virginia AI governance: applicable to in-scope Commonwealth AI use and requires registration/approval evidence when triggered.
- FedRAMP: conditional for federal cloud use; external assessment/authorization evidence required.
- NIST SP 800-171 Rev. 3: conditional when CUI is in scope.
- FIPS 140-3: conditional where validated cryptography is required; runtime module validation must be proven.
- CJIS Security Policy 6.1: conditional when CJI is in scope; applicable CSA/audit evidence is required.

## Command decision
Source-code controls establish readiness evidence. Deployment, organizational, cryptographic-module, data-scope, assessor, agency, profile/baseline selection, tailoring, and authorization evidence remain separate command gates and must never be inferred from CI success, catalog membership, or UI profile selection.
