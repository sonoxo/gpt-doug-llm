# XUNIA / Black House Information Boundary

Purpose: keep public-release material separate from sensitive, restricted, CUI-candidate, export-controlled-candidate, or genuinely classified material.

## Non-negotiable rule

This public GitHub repository is an **UNCLASSIFIED / PUBLIC-RELEASE surface only**. Do not commit classified information, CUI, controlled technical data, credentials, private keys, personal data, customer/government non-public data, proprietary partner material, or operational details that would create security risk.

A project name, defense topic, or confidential discussion does **not** make information classified. Only an authorized classification authority/source marking can establish a U.S. national-security classification. When status is uncertain, use `RESTRICTED_REVIEW` and keep the content off public GitHub until reviewed.

## Digital filing model

- `PUBLIC_RELEASE/` — approved public architecture, demos, sanitized documentation, public-source research, published interfaces.
- `UNCLASSIFIED_INTERNAL/` — ordinary internal engineering notes and planning that are not approved for public release. **Do not store this directory in the public repo; keep it in an access-controlled private workspace.**
- `RESTRICTED_REVIEW/` — uncertain sensitivity, NDA material, credentials, private infrastructure, vulnerability details, CUI/export-control candidates. **Never public GitHub.**
- `CLASSIFIED/` — only material explicitly marked/classified by an authorized source. **Never GitHub, ordinary cloud drives, ChatGPT, or unapproved systems. Use only the authorized classified system/environment.**

## Release gate

Every artifact must carry: `owner`, `system`, `source`, `classification_status`, `public_release`, `sensitivity_reason`, `reviewer`, `review_date`, and `declassification_or_release_basis` where applicable.

Allowed public transition:

`UNCLASSIFIED_INTERNAL -> REVIEW -> PUBLIC_RELEASE`

Uncertain material transitions:

`UNKNOWN -> RESTRICTED_REVIEW -> authorized review -> PUBLIC_RELEASE or approved controlled environment`

There is no automatic `CLASSIFIED -> PUBLIC_RELEASE` transition.

## System lanes

| Lane | Public-safe scope | Keep non-public by default |
|---|---|---|
| Zyra / Zyra Cloud | product descriptions, sanitized architecture, public APIs, demos | secrets, customer data, private endpoints, access topology |
| Black House | defensive security concepts, sanitized controls, CI/security status | exploit-sensitive findings, credentials, private telemetry, target-specific operational data |
| RVIA | public mission/architecture descriptions and public-source research | government/customer non-public material, sensitive operational intelligence, source-identifying data |
| VA3LM | sanitized model architecture, tests, benchmarks | private datasets, credentials, sensitive prompts/context, controlled source material |
| Wakeup3lm | public docs, diagrams, sanitized orchestration concepts | internal control paths, private infrastructure and privileged configuration |
| XUNIA | public platform architecture and interfaces | partner/customer confidential data, private tenancy and credentials |
| NXYZ | public cloud concepts and deployment docs | network topology, secrets, access material, private storage contents |
| AIP / Palantir plane | public integration contracts, capability gates, public product references | tenant IDs/details, tokens, non-public ontology/data, customer/government tenant content |

## Enforcement

1. Default uncertain content to `RESTRICTED_REVIEW`, not `CLASSIFIED`.
2. Never infer classification from project names or subject matter.
3. Strip secrets and sensitive operational details before public release.
4. Require human release review for government/partner/customer-derived material.
5. Never claim a Palantir tenant is connected or authorized without an authorized successful probe.
