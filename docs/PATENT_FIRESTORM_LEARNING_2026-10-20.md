# GPT-Doug / GPT-Doug-Max: firestorm patent learning (2026-10-20)

**Scope:** civilian wildfire-resilience research only. This update adds a versioned knowledge seed, not model-weight training or deployed hazard control.

## Source and confidence

A user-supplied **USPTO Patent Public Search 4.4.0** excerpt for `firestorm` contained 12 results. Detailed abstract, specification and seven claims were supplied only for **US 2026/0273318 A1**, *Shielded soffit vent assembly*, published September 17, 2026. The source upload has SHA-256 `054ab6305cfdfaed6e11811c0aae898aae1a578f8df5917914732b1fac4e0a93`.

Public descriptions were cross-checked with [Justia](https://patents.justia.com/patent/20260273318) and [PatSnap Eureka](https://eureka.patsnap.com/patent/US20260273318A1). The official PDF was not retrieved in this environment. Real-world performance, code compliance, rights, and live legal status remain unverified.

## Learning

The publication describes a screened soffit opening and **manually positionable** shield intended to block attic airflow during wildfire ember or severe wind risk. The source discusses composite materials, mounting options, and removable/retained shields. It does **not** describe an IoT-controlled or autonomous emergency system.

The independently proposed software use is a **read-only, provenance-aware wildfire/building-ventilation research dashboard and simulation knowledge graph**. This architecture is a GPT-Doug proposal, not a claim that the patent implements these software functions.

Canonical index seed: [us-20260273318-a1-shielded-soffit-vent-seed.json](../safety-shield/agents/knowledge/patents/us-20260273318-a1-shielded-soffit-vent-seed.json).

## Metadata-only result queue

The other search hits do **not** have reviewed claims or sufficient technical detail for design extraction:
- US 20260207979 A1 — Self-contained system for defense against wildfire-induced damage to structures
- US 20260194333 A1 — Optimized fragment geometry for an explosive projective device (safety-isolated; **no weapon-design extraction**)
- US D1127682 S — Aerial vehicle
- US D1126375 S — Patio heater
- US 20260079963 A1 — Data lakehouse energy/performance optimization
- US 20260079940 A1 — Database energy/performance optimization
- US D1118866 S — Patio heater
- US 20260072069 A1 — Power line fault detection
- US PP37238 P2 — Sedum plant named LOVE'S FIRE
- US 12491441 B2 — Information processing system
- US 20250321355 A1 — Environmental event monitoring

The above are discovery leads only. No patent performance or design claim is inferred from these titles.

## Verify

```sh
scripts/doug-max patent-scope show US-20260273318-A1
scripts/doug-max patent-scope match "firestorm wildfire shielded soffit vent attic ember intrusion" --json
scripts/doug-max patent-scope doctor
python3 -m pytest -q tests/test_firestorm_patent_scope.py
```

Before physical deployment, require qualified building/fire-safety engineering, relevant ventilation and building-code review, measured tests, emergency procedure analysis, and legal rights review. No automatic vent operation is authorized.
