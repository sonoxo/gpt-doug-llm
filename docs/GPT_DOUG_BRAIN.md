# GPT-Doug Brain Kernel

The `gpt_brain` package consolidates GPT-Doug's ontology, memory, provider, agent-chain and digital-clone concepts into one bounded orchestration kernel.

## Reliability contract

The brain is designed to fail visibly and degrade safely:

- ontology and status inspection work without a configured model;
- one specialist failure does not destroy the entire run;
- a failed memory archive does not discard a completed answer;
- provider failures return compact structured diagnostics instead of raw tracebacks;
- external action claims require evidence rather than model assertion;
- secret-like values are rejected from persistent brain memory.

## Runtime loop

1. Recall episodic, semantic and procedural memory.
2. Ground the task against `config/global-ontology.json`.
3. Route to specialist agents: ontology, research, builder and critic.
4. Run specialists in parallel through `agents.llm_backend`.
5. Preserve partial results if one specialist fails.
6. Run a critic pass over contradictions and unsupported claims.
7. Synthesize the final artifact with uncertainty and provenance.
8. Archive the outcome when memory is writable.

## One launcher

The repository launcher is the canonical path; package installation is not required for these modes:

    scripts/doug-max brain
    scripts/doug-max brain-doctor
    scripts/doug-max brain "build a medical cancer research ontology"
    scripts/doug-max brain-json "build a medical cancer research ontology"
    scripts/doug-max swarm "analyze the next highest-value build"
    scripts/doug-max brain-recall medical ontology cancer
    scripts/doug-max matrix

## Behavioral clone seeding

An authorized text transcript/export can seed episodic memory:

    scripts/doug-max clone ./chat-export.txt "chat-export:2026-09-25"

This reproduces authorized context and behavior patterns. It does not copy proprietary model weights, inaccessible platform state, or hidden model reasoning.

## Existing components reused

- `agents/llm_backend.py` — provider-neutral model access
- `config/global-ontology.json` — ontology source of truth
- `agents/agent_chain.py` — bounded recursive agent-chain pattern
- `doug_core/memory.py` — append-only memory precedent
- `gpt_chaos/digital_clone.py` — digital-clone policy model

## Command-center direction

The runtime is the backend for a Matrix/Minority-Report-inspired command center:

- live ontology graph;
- visible specialist swarm;
- evidence/provenance timelines;
- hypothetical scenario branches with confidence and uncertainty;
- voice/gesture-ready control surfaces;
- explicit LIVE / CACHED / SIMULATED / HYPOTHESIS / CONTRADICTED state labels.

Predictive output is treated as evidence-ranked hypothesis, not certainty.
