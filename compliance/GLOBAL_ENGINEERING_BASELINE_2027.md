# GPT-DOUG Global Cybersecurity & AI Engineering Baseline — 2027 Horizon

**Reviewed:** 2026-10-07  
**Purpose:** Global engineering-readiness map for GPT-DOUG / Eagle Eye.  
**Authority:** HUMAN-FIRST / ADVISORY-ONLY.

This baseline does not claim universal legal compliance. Cybersecurity and AI obligations
depend on the actual jurisdiction, sector, product, data, contract, role in the supply
chain, and system boundary. Certification and regulator/authority decisions remain
external.

## Universal engineering domains

1. Governance and accountability
2. Enterprise and AI risk management
3. Identity, MFA, privileged access, and service identities
4. Asset, software, model, and data inventory
5. Data classification, privacy, residency, retention, and transfer
6. Secure development, SBOM, provenance, vulnerability handling, and release evidence
7. Configuration baselines, hardening, change management, and drift detection
8. Cryptography, keys, secrets, and certificate lifecycle
9. Logging, monitoring, detection, evidence integrity, and observability
10. Incident response, regulator notification, forensics, and lessons learned
11. Backups, recovery, business continuity, resilience, RTO, and RPO
12. Third-party, cloud, supplier, and concentration risk
13. Zero trust, segmentation, device posture, and workload identity
14. AI lifecycle governance, impact assessment, TEVV, transparency, and human oversight
15. Continuous assessment, evidence, certification, and authorization tracking

## Global management-system baseline

- **ISO/IEC 27001:2022** for information security management.
- **ISO/IEC 42001:2023** for AI management systems.
- **ISO/IEC 42005:2025** for structured AI system impact assessment.
- **PCI DSS v4.0.1** when the system stores, processes, or transmits payment-card data.

These standards complement, but do not replace, jurisdiction-specific laws and sector rules.

## United States

GPT-DOUG tracks NIST CSF 2.0, NIST AI RMF, NIST AI 600-1, NIST SP 800-53/53A/53B,
NIST SP 800-171/171A Rev. 3, NIST SSDF, CISA Zero Trust Maturity Model, CMMC/DFARS,
FIPS 140-3 validation requirements, and FedRAMP where applicable.

### 2027 U.S. milestones

- **2027-01-01:** FedRAMP Consolidated Rules for 2026 become mandatory, subject to
  rule-specific applicability.
- **2027-06-11:** FedRAMP states that it will stop accepting applications for new
  Rev5 certifications.

## European Union

### EU AI Act

The AI Act is already in phased application. GPT-DOUG should maintain:

- AI system and model inventory
- role classification: provider, deployer, importer, distributor, GPAI provider, etc.
- prohibited-practice screening
- risk classification
- human oversight
- logging and traceability
- technical documentation
- robustness/cybersecurity evidence
- transparency and synthetic-content labeling where applicable
- impact assessment and serious-incident process

#### 2027 AI milestones

- **2027-08-02:** GPAI models placed on the market before 2 August 2025 must meet
  applicable GPAI obligations.
- **2027-12-02:** high-risk rules for Annex III use cases apply.
- **2028-08-02:** high-risk rules for AI embedded in regulated products are the next
  major horizon after 2027.

### Cyber Resilience Act

Reporting duties already apply from **2026-09-11** for actively exploited
vulnerabilities and severe incidents affecting products with digital elements.

The CRA becomes fully applicable **2027-12-11**. Engineering work should therefore
include:

- secure-by-design product requirements
- cybersecurity risk assessment
- vulnerability-handling policy and support-period records
- SBOM/component visibility
- coordinated vulnerability disclosure
- security-update process
- product security documentation
- 24-hour early-warning and 72-hour main-notification workflow
- evidence for final reporting and corrective action

### NIS2

For entities in scope through national transposition, maintain risk-management,
business-continuity, supply-chain, cryptography, access-control, incident-response,
and management-accountability evidence. NIS2 uses an early-warning / full-notification
pattern of 24 and 72 hours for reportable incidents.

### DORA

Financial entities and relevant ICT providers should maintain ICT risk management,
incident handling, resilience testing, third-party oversight, continuity, and
regulatory evidence. DORA has applied since 17 January 2025.

## United Kingdom

Track:

- NCSC Cyber Assessment Framework v4.0
- Cyber Governance Code of Practice
- AI Cyber Security Code of Practice
- Software Security Code of Practice
- sector-specific NIS and regulatory obligations where applicable

Use the UK material as a separate applicability layer rather than assuming that EU law
continues to apply automatically in the UK.

## Canada

Track:

- Canadian Centre for Cyber Security security/privacy controls and assurance catalogue
  effective 31 March 2026, aligned with NIST SP 800-53 Rev. 5
- OSFI Guideline B-13 for federally regulated financial institutions
- federal/provincial privacy rules according to the actual processing context

## Australia

Track:

- ASD Information Security Manual, September 2026 release
- Essential Eight Maturity Model
- applicable PSPF, IRAP, critical-infrastructure, privacy, and prudential requirements
  according to the actual deployment and customer

## Singapore

The Cybersecurity Act and 2024 amendments are active; key amendment provisions came
into force on 31 October 2025. Cloud and provider-owned systems can still fall within
critical-information-infrastructure responsibilities. Apply sector rules separately
for finance, healthcare, transport, and other regulated industries.

## India

The Digital Personal Data Protection Rules 2025 are now part of the active legal
landscape, with phased commencement. Each rule's effective date must be checked before
asserting applicability. Build data inventories, notice/consent records, processor
controls, breach handling, and data-principal request workflows so features can be
enabled per jurisdiction.

## Saudi Arabia

Track NCA Essential Cybersecurity Controls **ECC 2-2024** as the national engineering
control baseline for applicable entities, including governance, defense, resilience,
third-party security, and cloud/cyber requirements.

## Brazil

Track LGPD and ANPD regulations. Resolution 15/2024 established security-incident
communication requirements. Build a jurisdiction-aware incident workflow rather than
using one global notification timer for every breach.

## Universal 2027 risk priorities

- identity compromise and privilege abuse
- software supply-chain compromise
- cloud and configuration exposure
- ransomware and destructive disruption
- privacy/data loss and cross-border transfer failures
- third-party and concentration risk
- AI model/agent safety, misuse, traceability, and human-oversight failure
- known-vulnerability and zero-day exploitation
- cryptographic/key lifecycle weaknesses
- inadequate logging/evidence retention
- regulatory notification deadline failures
- untested backups and recovery
- shadow AI / unregistered models and agents
- vendor model or API changes without re-assessment

## Build requirements before calling GPT-DOUG production-ready

1. Dedicated durable production Postgres with encrypted backups and tested restore.
2. Federated OIDC/MFA and service/workload identities.
3. Short-lived credentials and centralized secrets/KMS strategy.
4. Complete software/model/data/supplier inventory.
5. SBOM + build provenance + release signing for every release.
6. Vulnerability disclosure and coordinated remediation process.
7. Jurisdiction-aware incident reporting engine.
8. Data classification, retention, residency, and transfer policy engine.
9. AI inventory, impact assessment, TEVV, transparency, and human-decision records.
10. Third-party risk register and concentration/exit plans.
11. Centralized metrics, logs, traces, alerting, and evidence retention.
12. Tested incident-response, ransomware, and disaster-recovery exercises.
13. Staging-to-production promotion, migrations, rollback, and change approval.
14. Continuous standards freshness checks.
15. Independent assessment/certification/authorization when required.

## Source-of-truth rule

Official regulator, standards-body, and government sources override this file.
The compliance registry is versioned and must be re-verified before material
certification, contract, regulatory, or market-entry decisions.
