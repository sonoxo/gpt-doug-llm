# U.S. Federal + Intelligence Community Security Alignment

**Applies to:** GPT-DOUG-LLM · Virginia-LLM · MAX-VA · RVIA · Palantir AIP/Ontology/Gotham/Apollo/Jupyter integration

## Status language

This repository implements a **public-guidance control alignment and assessment gate**. It does **not** claim a U.S. Space Force/DoD ATO, NSA approval, NASA authorization, CIA approval, Intelligence Community accreditation, or authorization to process classified information.

Formal authorization can only be issued by the responsible government organization and Authorizing Official for the actual deployed system, environment, data classification, users and mission.

## Alignment matrix

| Environment | Public basis | Repo enforcement |
| --- | --- | --- |
| U.S. Space Force / DoD | DoDI 8510.01 RMF; DoD AI Cybersecurity Risk Management Tailoring Guide; USSF Commercial Space Strategy; DoD Zero Trust principles | least privilege, fail-closed policy, continuous assessment flags, change control, human-gated writes, audit/provenance, no ambient authority |
| NSA / NSS | NSA Zero Trust CSIs; CNSA 2.0 and CNSS Policy 15 transition guidance; CNSSI-1253 mappings where applicable | HTTPS-only Foundry transport, exact-host pinning, same-host HTTPS redirect boundary, no unapproved classified mode, remote-model egress disabled by default |
| NASA | NPR 2810.1F; NIST SP 800-37; NIST SP 800-53 | NIST control-family gate, audit/change/identity/incident evidence expectations, assessment state rather than certification theater |
| CIA / Intelligence Community | Public ODNI ICD 502, ICD 503, ICD 703, ICD 731 and related IC directives | markings/provenance preservation, least privilege, auditability, classification gate, supply-chain evidence, explicit statement that non-public CIA requirements cannot be asserted as implemented |

## Runtime controls

Run:

```text
/palantir compliance
```

or:

```text
/palantir rmf
```

The response exposes:

- `assessment_state`: `assessment-ready` or `control-gap`;
- the active NIST-style control-family checks;
- Space Force/DoD, NSA/NSS, NASA, and CIA/IC alignment status;
- public source authorities;
- a release gate;
- explicit `certified=false`, `ato=false`, and `cia_approved=false` values until an authorized government process says otherwise.

## Fail-closed classification model

Default mode is:

```text
GOV_DATA_MODE=PUBLIC-UNCLASSIFIED
GOV_ALLOW_CLASSIFIED=false
GOV_CLASSIFIED_ENVIRONMENT_AUTHORIZED=false
GOV_ALLOW_REMOTE_MODEL_EGRESS=false
```

If classified processing is requested without an explicitly authorized classified environment, the compliance state becomes `control-gap` and the classified-processing control fails.

A public GitHub repository must never be treated as a classified processing environment.

## Required assessment evidence

Before government production use, collect and maintain at minimum:

1. system boundary and architecture documentation;
2. data classification and handling rules;
3. identity, MFA and least-privilege evidence;
4. audit logging, retention and review evidence;
5. secure configuration and change-management records;
6. vulnerability, dependency and supply-chain evidence;
7. incident response, contingency and recovery procedures;
8. control assessment results, POA&M/remediation tracking and retest evidence;
9. cryptographic implementation/validation evidence appropriate to the target environment;
10. the responsible agency's authorization/ATO/accreditation artifacts.

## Implemented transport hardening

The Foundry client now enforces:

- HTTPS-only base URLs and requests;
- exact configured-host allowlisting;
- redirects restricted to the same exact HTTPS host;
- rejection of cross-host and HTTP redirects before following them;
- write operations disabled by default;
- explicit human confirmation for terminal Ontology Actions;
- credential redaction in transport error details;
- no credentials persisted in the repository.

These controls reduce token-exfiltration and confused-deputy risk but do not replace Palantir enrollment permissions, agency network controls, approved cryptographic modules or formal authorization.

## Public source authorities

- DoD CIO — AI Cybersecurity Risk Management Tailoring Guide: https://dodcio.defense.gov/Portals/0/Documents/Library/AI-CybersecurityRMTailoringGuide.pdf
- U.S. Space Force — Commercial Space Strategy: https://www.spaceforce.mil/Portals/2/Documents/Space%20Policy/USSF_Commercial_Space_Strategy.pdf
- NSA — Zero Trust Cybersecurity Information Sheets: https://www.nsa.gov/Cybersecurity/ZIG/CSIs/
- NSA — Post-Quantum Cybersecurity Resources / CNSA 2.0: https://www.nsa.gov/Cybersecurity/Post-Quantum-Cybersecurity-Resources/
- NASA — NPR 2810.1F: https://nodis3.gsfc.nasa.gov/displayDir.cfm?Internal_ID=N_PR_2810_001F_&page_name=Preface
- ODNI — Intelligence Community Directives: https://www.dni.gov/index.php/who-we-are/organizations/policy-capabilities/ps/ps-related-menus/ps-related-links/policy-division/intelligence-community-directives
- NIST — SP 800-53 Rev. 5: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final

## CI enforcement

`.github/workflows/palantir-federal-compliance.yml` compiles the security modules and executes regression tests across Python 3.11 and 3.12. It explicitly verifies that classified mode fails closed and that the repository never self-asserts government certification or CIA approval.
