# THE BLACK HOUSE // PALANTIR RESEARCH CREDITS

This file defines attribution and citation rules for Palantir-associated research in GPT-DOUG-LLM / RVIA / The Black House.

## Primary interview source

- **Publisher:** Basis Points
- **Episode:** *Why Palantir Is Winning In The Era of Institutional Sovereignty ft. Chad Wahlquist*
- **Video:** https://www.youtube.com/watch?v=egr-UDWLZPI&t=2150s
- **Guest:** Chad Wahlquist
- **Public association:** Palantir Technologies — Architect

The episode is treated as a **credible Palantir-associated interview**, not as an official Palantir corporate publication.

## First-party Palantir corroboration

Technical claims should preferentially cite Palantir's own current documentation:

1. Architecture Center — https://www.palantir.com/docs/foundry/architecture-center/overview
2. Ontology overview — https://www.palantir.com/docs/foundry/ontology/overview
3. Ontology core concepts — https://www.palantir.com/docs/foundry/ontology/core-concepts
4. Object permissioning — https://www.palantir.com/docs/foundry/object-permissioning/overview
5. AIP Logic — https://www.palantir.com/docs/foundry/logic
6. AIP Evals — https://www.palantir.com/docs/foundry/aip-evals/overview
7. Automate — https://www.palantir.com/docs/foundry/automate
8. AIP Evolve — https://www.palantir.com/docs/foundry/aip-evolve/overview
9. Bring Your Own Model — https://www.palantir.com/docs/foundry/aip/bring-your-own-model
10. AIP security/privacy — https://www.palantir.com/docs/foundry/aip/aip-security
11. AIP Analyst capabilities — https://www.palantir.com/docs/foundry/aip-analyst/capabilities
12. AIP Analyst usage / provenance graph / skills — https://www.palantir.com/docs/foundry/aip-analyst/using-aip-analyst
13. SuperRepo overview — https://www.palantir.com/docs/foundry/superrepo/overview
14. August 2026 announcements — https://www.palantir.com/docs/foundry/announcements
15. Palantir public architecture post featuring Chad Wahlquist — https://www.linkedin.com/posts/palantir-technologies_inside-palantirs-ai-architecture-with-chad-activity-7234250372381319168-8R5n

## Research hierarchy

Use this source weighting for PR review:

| Tier | Source | Use |
| --- | --- | --- |
| `T1` | Current Palantir first-party docs / official Palantir publications | Architecture facts and product behavior |
| `T2` | Palantir employee interview or presentation with identity/role corroborated | Strategy, design philosophy, field observations |
| `T3` | Credible partner/community summaries linking original material | Discovery and contextual corroboration |
| `T4` | Social reposts / commentary | Leads only; never durable truth without corroboration |

## PR citation rules

A PR that changes architecture based on external research must:

- link the original source;
- identify whether the source is first-party, associated, or secondary;
- separate direct source claims from project inference;
- identify the relevant Palantir documentation when a technical claim can be corroborated;
- assign confidence (`LOW`, `MEDIUM`, `HIGH`, `VERY HIGH`);
- preserve unresolved gaps;
- avoid claiming Palantir endorsement, partnership, certification, access, or proprietary implementation knowledge;
- avoid copying proprietary source code or non-public materials;
- keep the implementation independent and open-source.

## Confidence language

- **VERY HIGH:** directly supported by current first-party Palantir documentation.
- **HIGH:** strongly supported by credible associated evidence and consistent with first-party docs.
- **MEDIUM:** plausible and source-linked, but exact wording/details are not fully corroborated.
- **LOW:** lead requiring further corroboration; do not promote into durable agent knowledge.

## Credit statement for reuse

> Research derived from public materials including Palantir Technologies documentation and a Basis Points interview with Palantir Architect Chad Wahlquist. GPT-DOUG-LLM / RVIA / The Black House is an independent open-source project and is not affiliated with or endorsed by Palantir Technologies.
