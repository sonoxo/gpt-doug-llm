# GPT-DOUG Global Incident / Regulatory Notification Matrix

**Reviewed:** 2026-10-07  
**Purpose:** Engineering workflow inputs only; legal counsel and responsible authorities
determine actual reportability and deadlines for a real event.

| Regime | Trigger / scope summary | Engineering timer | Evidence to preserve |
|---|---|---|---|
| EU NIS2 | Significant incident for an in-scope essential/important entity under national implementation | Early warning target: 24h; full notification target: 72h | discovery time, systems/services affected, severity, indicators, cross-border impact, remediation |
| EU Cyber Resilience Act | Actively exploited vulnerability or severe incident affecting a product with digital elements | Early warning: 24h; main notification: 72h; final-report workflows per CRA | product/version, vulnerability/incident details, exploitation evidence, affected markets, mitigation, corrective update |
| Brazil LGPD / ANPD Resolution 15/2024 | Personal-data incident capable of relevant risk or damage | Jurisdiction workflow must apply ANPD-prescribed deadlines; data-subject communication rule includes a 3-working-day deadline in the regulation | affected data categories, subjects, security controls, discovery date, impact, mitigation, communications, incident record |
| OSFI B-13 / Canadian financial sector | Reportable technology/cyber incident for federally regulated financial institutions | Immediate incident-classification and OSFI workflow | business impact, service disruption, containment, recovery, third parties, chronology |
| Singapore Cybersecurity Act | Incident/requirement affecting regulated CII or other designated systems | Apply CSA / sector-specific obligation after scope determination | asset/CII mapping, cloud/provider dependency, incident timeline, impact, response |
| India DPDP | Personal-data breach under the DPDP Act/Rules as phased into effect | Rule-specific timer loaded from current effective provision | data inventory, affected principals, notice records, processors, response and remediation |
| Contractual / customer | Contract, SLA, cyber-insurance, processor/subprocessor, or procurement obligation | Contract-specific | customer impact, evidence chain, contract clause, notification timestamps |
| Payment card | Cardholder-data event in PCI-scoped environment | PCI/acquirer/brand-specific | affected CDE, logs, forensic state, credentials, scope, containment |

## GPT-DOUG incident state machine

```text
DETECT
  -> VERIFY
  -> CLASSIFY DATA / SYSTEM / JURISDICTION / SECTOR
  -> PRESERVE EVIDENCE
  -> CONTAIN
  -> START ALL APPLICABLE TIMERS
  -> HUMAN / LEGAL REPORTABILITY DECISION
  -> REGULATOR / CUSTOMER NOTIFICATION
  -> RECOVER
  -> VERIFY
  -> ROOT CAUSE
  -> REMEDIATE
  -> AUDIT / LESSONS LEARNED
```

## Required incident fields

- incident ID and immutable discovery timestamp
- first-observed and first-known timestamps
- reporter and responsible human decision owner
- affected systems, products, versions, regions, customers, and data classes
- applicable jurisdictions and sector rules
- confidence and evidence provenance
- compromise indicators and relevant logs
- confidentiality / integrity / availability impact
- safety and fundamental-rights impact for AI systems where relevant
- supplier / cloud / model-provider involvement
- containment and recovery actions
- notification clocks, decisions, submissions, acknowledgements
- corrective actions and closure evidence

## Rule

Do not collapse all regimes into a single "72-hour breach rule." Different legal and
contractual triggers, clocks, recipients, and content requirements coexist. GPT-DOUG
should calculate candidate deadlines and present them to the responsible human
authority; it should not autonomously make legal reportability decisions.
