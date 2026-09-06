# THE BLACK HOUSE // INTEGRATIONS

This directory registers external platforms, public architecture references, and bounded interoperability contracts used by The Black House.

## Active entries

- [`crowdstrike-safemind-reference.json`](./crowdstrike-safemind-reference.json) — public SafeMind architecture reference mapped into a Black House-native paired-agent defensive loop. This is **not** a CrowdStrike/Falcon integration and includes no vendor model weights, telemetry, tenant access, credentials, proprietary harness code, or affiliation claim.
- [`palantir/`](./palantir/) — Palantir integration contracts and verification state.
- [`neptune-shield/`](./neptune-shield/) — Neptune Shield reference/integration material.
- [`xunidirect-youtube-cleaner.json`](./xunidirect-youtube-cleaner.json) — XuniDirect integration contract.

## SafeMind-derived Black House pattern

```text
AUTHORIZED / SYNTHETIC TARGET
        ↓
ADVERSARY_SIMULATOR
        ↓
ATTACK-PATH EVIDENCE
        ↓
DEFENSE_CLOSER
        ↓
SHADOW GLASS + ZYRA AUTHORIZATION
        ↓
BOUNDED REMEDIATION
        ↓
VERIFY + EVAL + AUDIT + ROLLBACK
        ↺
```

Machine-readable agent knowledge: [`../../safety-shield/agents/knowledge/safemind-inspired-defensive-loop-v1.json`](../../safety-shield/agents/knowledge/safemind-inspired-defensive-loop-v1.json)

Research brief: [`../../intel/briefings/2026-09-06-crowdstrike-safemind-agentic-defense.md`](../../intel/briefings/2026-09-06-crowdstrike-safemind-agentic-defense.md)

Source record: [`../../intel/sources/crowdstrike-safemind-2026-09-06.json`](../../intel/sources/crowdstrike-safemind-2026-09-06.json)
