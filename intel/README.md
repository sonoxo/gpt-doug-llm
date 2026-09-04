# 🏛️ THE BLACK HOUSE // INTELLIGENCE INDEX

This directory stores **source-traceable intelligence artifacts** for ZYRA, XUNIA, GPT-DOUG-LLM, VIRGINIA-LLM, and RVIA.

## Operating rule

```text
SOURCE CLAIM ≠ VERIFIED FACT
MODEL OUTPUT ≠ AUTHORITY
CONFIDENCE MUST FOLLOW EVIDENCE
```

Every intelligence item should preserve:

- source URL and retrieval context;
- provenance and framing notes;
- transcript/extraction status;
- independently verified facts;
- analyst assessment;
- confidence and gaps;
- disposition (`KEEP`, `REVIEW`, `QUARANTINE`, `REJECT`);
- links to ontology/workflow implications.

## Automated official-source watches

### White House Daily

[`intel/white-house/README.md`](./white-house/README.md) defines a daily first-party White House source monitor driven by GitHub Actions. It watches official White House News, Fact Sheets, Releases, Briefings & Statements, Remarks, Research, Executive Orders, and Presidential Memoranda; deduplicates canonical URLs; records provenance and content hashes; tags mission-relevant items; writes daily JSON/Markdown; and commits/pushes repository changes.

The source rule is explicit:

```text
WHITE HOUSE PUBLICATION = VERIFIED FACT THAT THE WHITE HOUSE PUBLISHED IT
WHITE HOUSE ASSERTION ≠ INDEPENDENTLY VERIFIED FACT
```

Workflow: [`.github/workflows/white-house-daily.yml`](../.github/workflows/white-house-daily.yml)

Collector: [`scripts/white_house_daily.py`](../scripts/white_house_daily.py)

## Current briefs

| Date | Source | Topic | State | Brief |
| --- | --- | --- | --- | --- |
| 2026-09-03 | freeCodeCamp.org `ug8W0sFiVJo` | Kali/Linux, scoped Nmap, wireless-security defense, Wireshark | `HIGH / AUTHORIZED-LAB` | [`Open brief`](./briefings/2026-09-03-freecodecamp-ethical-hacking-course.md) |
| 2026-09-02 | Basis Points / Chad Wahlquist `egr-UDWLZPI` | Institutional sovereignty, Ontology, model portability, FDE, agentic AI | `HIGH CONFIDENCE / PR-READY` | [`Open dossier`](./briefings/2026-09-02-palantir-basis-points-institutional-sovereignty.md) |
| 2026-09-02 | YouTube Short `uFFFRTrSosc` | What Palantir does / AIP architecture | `AMBER` | [`Open brief`](./briefings/2026-09-02-youtube-uFFFRTrSosc-palantir.md) |

## Machine-readable sources

- [`youtube-ug8W0sFiVJo.json`](./sources/youtube-ug8W0sFiVJo.json)
- [`youtube-egr-UDWLZPI.json`](./sources/youtube-egr-UDWLZPI.json)
- [`youtube-uFFFRTrSosc.json`](./sources/youtube-uFFFRTrSosc.json)
- [`the-cyber-news-protected-reference.json`](./sources/the-cyber-news-protected-reference.json)

## Protected cyber references

The Black House maintains a protected-reference registry for high-value recurring discovery sources. A protected reference is durable and should not be silently removed or downgraded, but it is **not** elevated above primary evidence.

```text
PROTECTED REFERENCE ≠ PRIMARY AUTHORITY
PROTECTED REFERENCE ≠ VERIFIED FACT
PROTECTED REFERENCE = DURABLE DISCOVERY + CORROBORATION INPUT
```

Registered protected reference:

- **Cyber Security News / @The_Cyber_News** — `https://x.com/The_Cyber_News`

Use it for rapid cyber-intelligence discovery and lead generation. Material vulnerability, breach, malware, attribution, or incident claims must be corroborated with affected-vendor/project advisories, CISA/CERT/NVD or equivalent first-party sources, primary researcher material, or additional independent reputable reporting before promotion to durable agent knowledge or consequential action.

Policy: [`PROTECTED_REFERENCES.md`](./PROTECTED_REFERENCES.md)

## Cyber learning layer

The Black House cyber-learning subsystem converts public cybersecurity material into bounded agent competencies rather than unrestricted attack automation.

- [`Training index`](../training/black-house-cyber/README.md)
- [`Authorized lab policy`](../training/black-house-cyber/AUTHORIZED_LAB_POLICY.md)
- [`Curriculum`](../training/black-house-cyber/CURRICULUM.md)
- [`Wireless defense`](../training/black-house-cyber/WIFI_DEFENSE.md)
- [`Packet analysis`](../training/black-house-cyber/PACKET_ANALYSIS.md)
- [`Evals`](../training/black-house-cyber/EVALS.md)
- [`Learning ontology`](../safety-shield/agents/knowledge/black-house-ethical-hacking-course-ontology.json)
- [`Learning validator`](../scripts/validate_black_house_cyber_learning.py)

## Palantir-associated research standard

- [`PALANTIR_RESEARCH_CREDITS.md`](./PALANTIR_RESEARCH_CREDITS.md) — source hierarchy, attribution, confidence language, required first-party docs.
- [`PR_COLLABORATION.md`](./PR_COLLABORATION.md) — research-driven pull request contract and merge gate.
- [`assets/palantir-sovereignty-research-map.svg`](./assets/palantir-sovereignty-research-map.svg) — animated research/corroboration architecture.

### Confidence hierarchy

| Confidence | Meaning |
| --- | --- |
| `VERY HIGH` | Current first-party documentation directly supports the claim |
| `HIGH` | Credible associated source + strong first-party corroboration |
| `MEDIUM` | Credible source, but material detail remains incompletely verified |
| `LOW` | Discovery lead only; do not promote to durable agent knowledge |

## Agentic control plane

- [`AIP Agentic Workflows`](../safety-shield/AIP_AGENTIC_WORKFLOWS.md)
- [`RVIA Agentic Core`](../safety-shield/agents/knowledge/rvia-agentic-core.json)
- [`Palantir AI FDE Automate knowledge`](../safety-shield/agents/knowledge/palantir-ai-fde-automate-2026-08.json)
- [`External model egress policy`](../safety-shield/policies/external-model-egress.rego)
- [`External model registry`](../safety-shield/model-registry/external-model-registry.schema.json)
- [`SHADOW GLASS`](../safety-shield/SHADOW_GLASS.md)
- [`Safety Shield`](../safety-shield/README.md)

## Source lifecycle

```text
DISCOVER
  ↓
CAPTURE SOURCE RECORD
  ↓
TRANSCRIPT / EXTRACT WHEN AVAILABLE
  ↓
SEPARATE CLAIM FROM FACT FROM INFERENCE
  ↓
CORROBORATE WITH PRIMARY DOCUMENTATION
  ↓
SCORE CONFIDENCE
  ↓
MAP INTO ONTOLOGY / AGENT SKILL
  ↓
RUN WORKFLOW / SECURITY / EVALS
  ↓
PUBLISH BLACK HOUSE BRIEF
  ↓
PR REVIEW
  ↓
MERGE → AUDIT → RETAIN GAPS
```

## Independence

The Black House is an independent open-source research component. References to Palantir Technologies, its products, employees, documentation, or public materials are for research, interoperability, and attribution only and do not imply endorsement, affiliation, certification, contract, customer status, or access to proprietary systems. References to White House or U.S. Government sources identify public primary-source material only and likewise do not imply endorsement, affiliation, certification, contract status, or governmental authority. Protected cyber references identify public reporting sources only and do not imply endorsement, affiliation, partnership, or verification of every claim they publish.
