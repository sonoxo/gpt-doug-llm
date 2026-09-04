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
11. **Protect durable references without confusing them with authority.** Sources registered under `intel/PROTECTED_REFERENCES.md` remain preferred discovery/corroboration inputs, but claims still require evidence-tier validation before they become durable knowledge or drive consequential action.

## Protected cyber-intelligence references

GPT-DOUG-LLM and the fleet inherit The Black House protected-reference standard in [`../../../intel/PROTECTED_REFERENCES.md`](../../../intel/PROTECTED_REFERENCES.md). The owner-registered Cyber Security News / `@The_Cyber_News` source is retained as a protected discovery and corroboration reference. Its posts/articles are **not** primary authority or verified fact by default; vulnerability, breach, malware, attribution, and incident claims should be corroborated against vendor/project advisories, CISA/CERT/NVD or equivalent primary sources, primary researcher material, or additional independent reporting before promotion.

Machine-readable registration: [`../../../intel/sources/the-cyber-news-protected-reference.json`](../../../intel/sources/the-cyber-news-protected-reference.json).

## Palantir platform routing

`palantir-stack-v1` gives the fleet one provider-aligned routing model for the requested Palantir stack:

```text
AIP          → agent reasoning / workflows / automations / evals
Ontology     → governed objects / links / properties / actions / state
Gotham       → authorized mission + intelligence operational view
Apollo       → governed release + software deployment plane
JupyterLab   → Foundry Code Workspace for notebooks, analysis and models
```

The existing live adapter is the Foundry/Ontology REST bridge. AIP, Gotham, Apollo and JupyterLab are capability-gated and are never treated as provisioned merely because a local flag is enabled. The operator's Palantir enrollment, permissions and deployment configuration remain authoritative.

The requested `jupiter` label is normalized to **JupyterLab**, matching current Palantir Code Workspaces documentation.

See [`palantir-stack-v1.json`](./palantir-stack-v1.json) and [`../../../docs/PALANTIR_FOUNDRY.md`](../../../docs/PALANTIR_FOUNDRY.md).

## MAX-VA defensive cyber skill

`max-va-mainframe-defensive-pentest-v1` extends the shared profile with authorized mainframe security training for Virginia-LLM / RVIA / GPT-DOUG-LLM / MAX-VA-LLM.

The module teaches:

- mainframe architecture and trust-boundary analysis;
- TN3270, CICS, JES and RACF security concepts;
- sandbox attack-surface inventory;
- authorization and least-privilege review;
- detection engineering and incident reconstruction;
- hardening, segmentation and encryption review;
- purple-team validation where every simulated weakness is paired with prevention, detection and retesting.

The authorization gate limits offensive simulation to operator-owned systems, explicitly authorized targets, CTFs, training ranges and disposable labs. Unknown or real-world third-party targets are redirected to defensive analysis or sandbox exercises.

See [`mainframe-defensive-pentest-v1.md`](./mainframe-defensive-pentest-v1.md).

## AIP alignment

The profile follows current public Palantir AIP concepts:

- AIP Logic chains blocks such as LLM use, Ontology queries, actions, functions, conditions and loops.
- LLMs request tools; AIP Logic executes those requests inside the invoking user's permissions.
- AIP Chatbot Studio equips assistants with bounded enterprise context and tools.
- Automate can execute Logic or stage Ontology edits for human review.
- AIP Evals uses test cases, evaluators, metrics, comparisons and repeated runs to manage LLM nondeterminism.

## Video sources

Registered user-supplied references include:

- `https://www.youtube.com/watch?v=vgwql8Mv1CE`
- `https://www.youtube.com/watch?v=25iMrJDyIDk`

A reliable transcript was not recoverable for these sources during their respective updates. The fleet therefore does not invent lessons from unseen audio. Publicly verifiable topic-level context may be registered with provenance, while detailed source claims remain pending transcript review.

## Canonical files

- [`rvia-agentic-core.json`](./rvia-agentic-core.json) — machine-readable knowledge profile.
- [`palantir-stack-v1.json`](./palantir-stack-v1.json) — Palantir AIP/Ontology/Gotham/Apollo/Jupyter routing contract.
- [`mainframe-defensive-pentest-v1.md`](./mainframe-defensive-pentest-v1.md) — MAX-VA authorized mainframe security training module.
- [`../fleet-24.json`](../fleet-24.json) — fleet inheritance declaration.
- [`../agentic_builder.py`](../agentic_builder.py) — blueprint generator for new agents.
- [`../summon.py`](../summon.py) — verifies the fleet knowledge profile at startup.
