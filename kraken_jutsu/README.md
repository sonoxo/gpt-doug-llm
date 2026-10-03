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

## Actor–Narrative–Cyber verification

`narrative_intel.py` adds a second, incident-focused reasoning path built around the invariant **CLAIM != COMPROMISE**.

```text
EVENT -> NARRATIVE -> ACTOR -> MOTIVATION -> TARGET -> TTP
      -> OBSERVABLE -> IMPACT -> DEFENSE -> CONFIDENCE
```

Claims move through `CLAIMED`, `CORROBORATED`, `VERIFIED_INCIDENT`, `DISPUTED`, or `RETRACTED`. A verified incident requires multiple independent sources plus authoritative and technical corroboration; actor self-claims alone can never establish compromise.

See [`ACTOR_NARRATIVE_CYBER.md`](./ACTOR_NARRATIVE_CYBER.md) for the schema, evidence model, example, and acceptance properties.

Run the narrative verification tests from repository root with:

```bash
python -m pytest tests/test_kraken_narrative_intel.py -q
```

Run the existing ontology tests with:

```bash
python -m pytest kraken_jutsu/test_ontology.py -q
```
