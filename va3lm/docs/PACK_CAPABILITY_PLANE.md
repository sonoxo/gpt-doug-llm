# BIG VIRGINIA // PACK Capability Plane

VA3LM uses `sonoxo/pack` as an architectural reference for capability separation and engineering discipline.

PACK is explicitly marked **ALPHA / not intended for production use** in its own README. Big Virginia therefore does not treat PACK package existence as proof of production readiness. VA3LM keeps its own tests, security checks, approval gates, deployment verification, and evidence as the authoritative boundary.

## Adaptation map

| PACK area | Big Virginia use |
|---|---|
| `packages/core` | shared contracts and primitives |
| `packages/auth` | operator / Foundry auth boundaries |
| `packages/schema` | ontology and capability schemas |
| `packages/document-schema` | structured evidence contracts |
| `packages/state` | agent workflow + approval state |
| `packages/codegen` | typed generation patterns |
| `packages/sdkgen` | generated integration/client boundary |
| `packages/app` | VA3LM 8088 command-center surface |
| `packages/create-app` | VA/RVIA app scaffolding blueprint |
| `packages/monorepo` | CI, consistency and release discipline |

## Runtime visibility

```bash
va3lm capabilities
```

```text
GET /api/capabilities
GET /api/status
```

The capability registry lives in `src/va3lm/capabilities.py` and is intentionally dependency-light so the Python VA3LM runtime does not import an alpha TypeScript package tree directly.

## Engineering policy

1. Harvest patterns, contracts, tests and repository discipline from PACK.
2. Do not blindly vendor alpha packages into the VA3LM runtime.
3. Keep human approval before write/publish actions.
4. Require VA3LM-owned tests and security gates for adapted capability areas.
5. Mark blueprint-only capability areas clearly until implemented and verified.
