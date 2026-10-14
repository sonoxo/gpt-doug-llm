# GPT-Doug Federal Q-Day: 24-Agency PQC Readiness Framework

**Project state: assessment toolkit, NOT federal production deployment.** This is an offline, read-only planning and evidence-normalization utility for the 24 CFO Act agencies named by GAO-27-108740. It does not connect to federal systems, scan networks, push configurations, migrate cryptography, submit memoranda, issue ATOs, or represent federal approval. Any agency-specific status remains **NOT_INDEPENDENTLY_VERIFIED** without actual agency-reviewed evidence. Do not store real federal vulnerability, system, cryptographic, IP or classified inventory details in this public GitHub repository.

## Governing sources and scope

- **OMB M-26-15, June 24, 2026:** https://www.whitehouse.gov/wp-content/uploads/2026/06/M-26-15-Execution-of-the-Migration-to-Post-Quantum-Cryptography.pdf
- **EO 14412, June 22, 2026:** https://www.whitehouse.gov/presidential-actions/2026/06/securing-the-nation-against-advanced-cryptographic-attacks/
- **NIST PQC standards:** https://csrc.nist.gov/Projects/post-quantum-cryptography (FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA)
- **GAO-27-108740, October 6, 2026:** https://files.gao.gov/reports/GAO-27-108740/index.html
- **NSA CNSA 2.0/NSS guidance:** https://www.nsa.gov/Cybersecurity/Post-Quantum-Cybersecurity-Resources/

OMB M-26-15 **does not apply to National Security Systems**. Even agencies operating NSS have a separate non-NSS planning lane under this toolkit. NSS cryptography requires applicable NSA/CNSS requirements and authorization; this tool does not assess classified or NSS environments.

## Federal milestones

| Timing | Required direction under M-26-15 |
|---|---|
| October 22, 2026 | 120 days after June 24: agency PQC Migration Plan to OMB and ONCD |
| 2026–2027 | Governance, prioritized inventory, assessment, and migration strategy |
| 2027–2028 | Pilots and early migration |
| January 2, 2030 | TLS 1.3 or successor support |
| By December 31, 2030 | PQC key establishment for high-value and high-impact priority systems, including highly sensitive data systems; ensure crypto agility |
| 2031 | PQC digital signatures for the prioritized systems; ensure crypto agility |
| 2035 | Risk-based completion of remaining systems |

The Q-Day threat is a cryptographically relevant quantum computer (CRQC), **not a known presently deployed universal capability**. "Harvest now, decrypt later" makes data longevity and risk-based modernization urgent even before a CRQC exists.

## Operate locally (Python standard library only)

From the checked-out repository root:

```bash
python -m agents.quantum_day requirements
python -m agents.quantum_day seed --output /tmp/qday24-seed.json
python -m agents.quantum_day assess --input /tmp/qday24-seed.json --output /tmp/qday24-assessment.json
python -m agents.quantum_day ontology --input /tmp/qday24-seed.json --output /tmp/qday24-ontology.json
python -m unittest agents.tests.test_quantum_day -v
```

The `seed` command includes 24 agencies with **zero supplied evidence**. The `assess` command reports missing controls, sanitized high-level asset-priority metadata, and explicitly no independently verified ready agencies. The `ontology` command emits typed agency/control nodes and evidence-state relationships so GPT-Doug can consume the evidence graph without creating compliance claims.

## Evidence submission and offline prioritization

Use an agency-controlled local workspace. Each agency can supply a `controls` dictionary keyed by a documented control ID. A recorded evidence reference requires `reference`, `reviewer`, `reviewed_at` (timezone-aware ISO-8601) and `source_type` (`agency_attestation`, `official_public_record`, `independent_assessment`, or `test_report`). A reference is *documented*, not automatically authenticated or independently verified.

For per-system prioritization supply only pseudonymous `token`, `algorithms`, `purposes`, `high_value_asset`, `impact`, `sensitivity`, optional `protect_until_year` and `crypto_agile`. **No hostname, IP, endpoint URL, system name, secrets or actual inventory file is permitted by the validator.** Scoring: P0 for vulnerable public-key algorithms combined with high-value, high-impact, long-lived sensitive information or logical access; P1 for other vulnerable/unknown or non-agile crypto; P2 for implementation-validation only. P2 is **not** a claim of PQC compliance or FIPS 140-3 cryptographic module validation. RSA, ECDH, ECDSA, DSA and related public-key mechanisms are treated as quantum-vulnerable; ML-KEM, ML-DSA and SLH-DSA are classified only by claimed names, not verified deployment.

Sample authorized local metadata, after modifying a copy of the seed file:

```json
{
  "token": "ASSET_0001",
  "algorithms": ["RSA-2048"],
  "purposes": ["key_establishment"],
  "high_value_asset": true,
  "impact": "high",
  "sensitivity": "high",
  "protect_until_year": 2038,
  "crypto_agile": false
}
```

These sample values are fictional and must not be interpreted as findings for any particular agency.

## Agency execution roadmap

1. **Now through October 22, 2026:** Agency leaders designate a PQC lead, enumerate applicable non-NSS scope, produce the nine M-26-15 plan sections, document gaps without claiming completion, and have authorized officials review and submit via the official OMB channel. This repository does not send the submission.
2. **2026–2027:** Integrate HVA, high-impact, identity/PKI and long-lived-data inventories with cryptographic discovery and CBOM; verify provenance, system owners, vendor support, costs and schedules.
3. **2027–2028:** Run agency-authorized pilots for approved crypto modules, TLS 1.3 and PQC-capable protocols; test latency, interoperability, rollback, identity, HSM/KMS, signatures, and zero-trust dependencies.
4. **2028–2031:** Modernize highest-priority key establishment, then digital signatures. Validate downgrade resistance, vendor products, FedRAMP shared responsibility, configuration-driven algorithm changes, and non-migratable replacement plans.
5. **2031–2035:** Finish remaining migrations and continuously refresh inventories, evidence, budgets, test results, exception approvals and risk registers.

### Minimum agency migration-plan sections (Appendix B, OMB M-26-15)

Risk-based system prioritization; milestone timelines; TLS 1.3 testing/deployment timeline; inventory methodology and automation; crypto agility architecture; third-party coordination; funding/personnel estimate; migration risk management; and governance roles/responsibilities. The prototype models these as evidence-tracked controls, not as automatically completed statements.

## GAO evidence gap

The October 2026 GAO report found none of the 24 CFO Act agencies fully satisfied the reviewed preparatory practices (inventory, funding assessment and testing), and made 89 recommendations in the underlying sensitive report. Those findings are **not** transformed into individual asset or agency compliance scores here. This tool has no credentials, privileged agency access, implied authorization, or classified processing environment.

