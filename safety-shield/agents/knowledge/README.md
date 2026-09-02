# RVIA Agentic Knowledge Core

`rvia-agentic-core-v1` is the shared runtime knowledge profile for the GPT-LLM / Virginia-LLM / RVIA / ZYRA / XUNIA / TheBlackHouse agent ecosystem.

## What “learn” means here

The repository does **not** claim to retrain proprietary model weights. Instead, every fleet agent inherits a versioned knowledge contract at runtime: the same agentic loop, tool semantics, memory rules, handoff contract, eval requirements, policy gates and release criteria.

```text
MISSION
  ↓
CLASSIFY + RETRIEVE MINIMUM CONTEXT
  ↓
PLAN BOUNDED STEPS
  ↓
REASON
  ↓
REQUEST TOOL
  ↓
SHADOW GLASS POLICY
  ↓
EXECUTE BOUNDED ACTION
  ↓
VALIDATE + AIP-STYLE EVAL
  ↓
MEMORY / HANDOFF (IF APPROVED)
  ↓
GLASS ONION AUDIT
  ↓
ROLLBACK OR RELEASE
```

## Core agent-building rules

1. **No ambient authority.** An agent can propose a tool call; policy and runtime permissions decide whether it executes.
2. **Minimum context.** Retrieve only the objects, properties and documents required for the mission.
3. **Deterministic before generative.** Prefer explicit functions/actions for known operations; use an LLM for ambiguity, synthesis and planning.
4. **Separate stages.** Retrieval, reasoning, action, validation, eval and audit are distinct steps.
5. **Staged writes.** Material or uncertain changes should become proposals for human review.
6. **Evaluate before release.** Fixed test cases and negative tests must cover grounding, tool abuse, prompt injection, failure recovery and rollback.
7. **Govern memory.** Persistent memory needs purpose, owner, classification, retention and lineage.
8. **Re-authorize handoffs.** Agent B does not inherit Agent A's credentials, unrestricted context or tools.
9. **Evidence over confidence theater.** Intel claims retain provenance, confidence and gaps.
10. **Fail closed.** Unknown identity, source, permission, environment or model boundary is not an implicit allow.

## AIP alignment

The profile follows current public Palantir AIP concepts:

- AIP Logic chains blocks such as LLM use, Ontology queries, actions, functions, conditions and loops.
- LLMs request tools; AIP Logic executes those requests inside the invoking user's permissions.
- AIP Chatbot Studio equips assistants with bounded enterprise context and tools.
- Automate can execute Logic or stage Ontology edits for human review.
- AIP Evals uses test cases, evaluators, metrics, comparisons and repeated runs to manage LLM nondeterminism.

## Video source

User-supplied reference: `https://www.youtube.com/watch?v=vgwql8Mv1CE`

The source is registered in the knowledge graph, but a reliable transcript was not recoverable during this update. The fleet therefore does not invent lessons from unseen audio. When a reliable transcript becomes available, it can be converted into claim-level knowledge with provenance and confidence.

## Canonical files

- [`rvia-agentic-core.json`](./rvia-agentic-core.json) — machine-readable knowledge profile.
- [`../fleet-24.json`](../fleet-24.json) — fleet inheritance declaration.
- [`../agentic_builder.py`](../agentic_builder.py) — blueprint generator for new agents.
- [`../summon.py`](../summon.py) — verifies the fleet knowledge profile at startup.
