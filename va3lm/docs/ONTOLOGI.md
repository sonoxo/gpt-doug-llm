# ONTologi — Virginia/RVIA Seed Language

ONTologi is a compact, provenance-aware knowledge language for VA3LM / Virginia / RVIA. It improves structured retrieval and reasoning context; it is **not** a claim that this repository has created artificial superintelligence or trained a new foundation model.

## Syntax

```text
ONTOLOGI 1.0
SEED concept:ontology Concept "Typed knowledge graph" status=VERIFIED confidence=1.0 tags=ontology,knowledge
SEED source:example Source "https://example.com" status=CANDIDATE confidence=0.0 tags=source,pending-verification
LINK source:example EVIDENCES concept:ontology
```

Supported seed types: `Agent`, `Capability`, `Claim`, `Concept`, `Evidence`, `Rule`, `Source`, `System`.

Supported links: `CORROBORATES`, `DERIVED_FROM`, `EVIDENCES`, `GOVERNS`, `REQUIRES`, `SUPPORTS`, `TEACHES`, `USES`.

Knowledge states are deliberately explicit:

- `CANDIDATE` — observed or supplied, but not accepted as established knowledge.
- `VERIFIED` — promoted with sufficient confidence/evidence.
- `REJECTED` — known-bad or intentionally excluded.

## Virginia/RVIA learning model

`SOURCE → CANDIDATE SEED → LINK → EVIDENCE → PROMOTION → RETRIEVAL → PLAN`

The engine can stage new seeds immediately, but promotion to `VERIFIED` requires at least one evidence identifier and confidence of 0.7 or higher. Candidate material can still be retrieved with its status exposed, so planners can distinguish hypotheses from trusted context.

The user-supplied YouTube reference `https://www.youtube.com/watch?v=wzgkc6Iegx8` is seeded only as a `CANDIDATE Source`. No claims from that video are asserted until its content is independently retrieved and verified.

## Core files

- `src/va3lm/ontologi.py` — parser, validator, compiler, retrieval engine, governed learning operations.
- `knowledge/core.ontologi` — editable canonical seed program.
- `tests/test_ontologi.py` — parser, retrieval, candidate-source and promotion-gate tests.
