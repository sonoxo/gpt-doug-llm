# ZYRA Language

ZYRA is the TypeScript-oriented vibe-coding language layer for GPT-DOUG-LLM. Its core contract is deterministic intent preservation: user-specified names, routes, copy, features, and constraints are recorded before generation and must not be silently removed or renamed.

## First-class goals

- `.zyra` source files
- `strict true` for deterministic validation behavior
- `verbatim true` for exact intent preservation
- `build verbatim """..."""` for natural-language application requirements
- a generated requirement manifest that can be checked by downstream builders and reviewers
- TypeScript-compatible generated output
- fail loudly rather than report success when required intent is missing

## Example

```zyra
app ZyraEnterprise {
  language typescript
  strict true
  verbatim true

  build verbatim """
Create a streaming dashboard.
- live chat
- viewer count
- emoji reactions
Do not rename requested features.
Do not silently remove functionality.
"""
}
```

## Compile

```bash
python3 dougctl.py zyra-build examples/zyra-enterprise.zyra
```

By default this creates:

```text
build/zyra/zyra.manifest.json
build/zyra/zyra.generated.ts
```

The manifest preserves the complete source text and extracts explicit required items and forbidden changes. In verbatim mode the target score is `100`, meaning downstream implementation and verification layers should not declare completion until every locked requirement is satisfied.

## Current compiler boundary

Version 1 is intentionally small and deterministic. It compiles source intent into a locked intermediate representation and TypeScript spec. It does not yet generate an entire React/Fastify/Postgres application on its own. Full application generation should be implemented as a downstream builder that consumes `zyra.manifest.json`, emits code, runs tests, and compares the result to the locked requirements before reporting success.
