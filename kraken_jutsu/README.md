# 🐙 Kraken Jutsu — OSINT + Government Ontology Judgment

This module adds a provenance-first intelligence/judgment layer to `gpt-doug-llm` / `krakenXYZ`.

## Evidence flow

```text
OSINT Industries ─┐
CISA KEV ─────────┤
CISA Vulnrichment ├─> NORMALIZE -> CORROBORATE -> ONTOLOGY JUDGE -> D / O-D
ATT&CK / Decider ─┤
NIST OSCAL/800-53 ┘
```

`O-D` means defensive action plus authorized lab/digital-twin adversary simulation. It does not authorize active intrusion against arbitrary systems.

## Upstream decision

| Upstream | Decision | Reason |
|---|---|---|
| `cisagov/kev-data` | CONSUME | authoritative machine-readable KEV feed |
| `cisagov/vulnrichment` | CONSUME | CISA CVE/SSVC enrichment; no downstream fork needed |
| `cisagov/Decider` | OPTIONAL FORK | fork only if Kraken needs the guided ATT&CK mapping UI/content authoring layer |
| `usnistgov/OSCAL` | CONSUME SCHEMA | control/assessment ontology |
| `usnistgov/oscal-content` | CONSUME CONTENT | SP 800-53 catalogs/baselines |
| `mitre-attack/attack-stix-data` | CONSUME DATA | ATT&CK behavior graph |
| `cisagov/Malcolm` | ADAPTER LATER | valuable network telemetry, too large to merge into the kernel |

## OSINT Industries

Official API integration uses `POST https://api.osint.industries/v2/request` with an operator-provided API key. The adapter also supports offline JSON-export normalization so Kraken can work without paid API calls.

The integration fingerprints queries and treats provider output as untrusted evidence until corroborated. Raw provider responses should remain case-scoped/ephemeral rather than becoming permanent global memory.

## Judgment

`OntologyJudge` combines evidence into:

- `verdict`
- `priority` (0-10)
- `confidence`
- `provenance`
- mapped vulnerabilities / ATT&CK behaviors / NIST controls / OSINT providers
- `recommended_mode`: `d` or `od`

Run tests from repository root with:

```bash
python -m pytest kraken_jutsu/test_ontology.py -q
```
