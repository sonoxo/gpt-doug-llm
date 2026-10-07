# GPT-DOUG Security Policy

## Supported development line

GPT-DOUG is actively developed. Security fixes are expected on the current supported
integration and release branches. Older experiments and generated demos should not be
treated as production security boundaries.

## Reporting a vulnerability

Do not publish exploit details in a public issue. Report suspected vulnerabilities to
`security@sonoxo.com` with the affected component, reproduction conditions, impact,
and any supporting evidence. Do not include passwords, tokens, regulated data, or
third-party secrets in the report.

## Security operating principle

GPT-DOUG is **HUMAN-FIRST** and **ADVISORY-ONLY** for consequential decisions.

The AI control plane may analyze, correlate, compare, explain, prioritize, and
recommend. It does not provide a general-purpose autonomous execution surface for
consequential actions. Human authorities remain responsible for decisions, and any
implementation occurs through separately authorized systems and procedures.

The public platform explicitly separates simulation and public-context data from
regulated or mission-restricted environments.

## Current platform controls

| Area | Engineering control |
|---|---|
| Identity | Explicit bearer-token roles for director, analyst, auditor, and client; production demo auth disabled |
| Authorization | Route-level role checks and workspace isolation |
| Audit | HMAC hash-chained audit records with chain verification |
| Provenance | Source identifiers, provenance locators, confidence, digests, and event metadata |
| Browser boundary | Explicit CORS origin list, no wildcard origin, no browser credentials |
| HTTP hardening | No-sniff, no-referrer, frame denial, restricted browser permissions, API no-store headers |
| Realtime | Public WebSocket/REST history limited to PUBLIC, TRAINING, and SIMULATION event classes |
| Event policy | Operational weapon-control, target-selection, strike-planning, payload-release, lethal-engagement, and real-person hostile-classification event types are rejected |
| AI authority | Advisory records require a human decision record; the advisory API does not execute the recommendation |
| Health | Separate liveness, readiness, metrics, and audit-chain verification |
| Supply chain | CI compiles, tests, lints, scans, audits dependencies, and is being extended to produce SBOM evidence |
| Infrastructure | Version-controlled Render configuration plus separate local and cloud launch paths |

## Data boundaries

The public Eagle Eye and GPT-DOUG Core demonstration environment is for
**PUBLIC / TRAINING / SIMULATION** information.

FCI, CUI, National Security System data, classified information, export-controlled
technical data, law-enforcement-sensitive data, protected health information, or
other regulated datasets require a separately approved architecture, handling rules,
identity model, cryptographic boundary, logging plan, retention policy, and applicable
authorization. Do not upload such data to the public demonstration environment.

## U.S. government engineering baseline

The project tracks engineering evidence against relevant U.S. references including:

- NIST Cybersecurity Framework 2.0
- NIST AI Risk Management Framework and NIST AI 600-1
- NIST SP 800-53 Rev. 5, SP 800-53A, and SP 800-53B
- NIST SP 800-171 Rev. 3 and SP 800-171A Rev. 3
- NIST SP 800-218 Secure Software Development Framework
- CISA Zero Trust Maturity Model 2.0
- DoD CMMC / applicable DFARS cybersecurity clauses
- FIPS 140-3 validation requirements when applicable
- FedRAMP requirements when the scoped cloud service requires federal authorization

These references are an **engineering baseline**, not a certification statement.

GPT-DOUG must not claim CMMC status, FedRAMP authorization/certification, FIPS module
validation, RMF authorization/ATO, CUI enclave approval, or NSS/classified
authorization without the applicable external evidence and responsible authority.

## Deployment and secrets

Production deployments must:

1. Disable demo authentication.
2. Use unique generated secrets outside source control.
3. Use a durable managed database for persistent event, case, and audit data.
4. Restrict browser origins and administrative interfaces.
5. Separate production, staging, test, and public demonstration data.
6. Rotate credentials after suspected exposure.
7. Back up persistent data and verify restore procedures.
8. Record material security changes in the audit/evidence trail.

The current Render public Core remains an engineering/demo boundary until its durable
database, production identity, external assessment, and authorization requirements
are satisfied.

## Cryptography

Do not label a deployment "FIPS compliant" merely because it uses a particular
algorithm. Where FIPS requirements apply, identify the actual cryptographic modules
in use and verify their applicable CMVP validation and configuration.

## Software supply chain

Release evidence should include dependency locks, vulnerability scanning, an SBOM,
build provenance, source revision, test results, and release/deployment identifiers.
Generated artifacts and containers should be traceable to the source revision that
created them.

## Incident response

Security incidents should preserve timestamps, affected components, source revision,
deployment ID, logs, audit-chain verification results, containment actions, recovery
steps, and post-incident remediation evidence. Do not destroy evidence during
containment or recovery.

## Known gaps

Current known production-readiness gaps include managed durable Postgres for the new
Core deployment, federated OIDC/MFA, complete release SBOM/provenance evidence,
tested backup/restore objectives, production-grade centralized observability, and any
external assessment/authorization required by a specific contract or agency.

Security readiness is continuous. Passing internal tests or deploying successfully
does not by itself establish a government authorization.
