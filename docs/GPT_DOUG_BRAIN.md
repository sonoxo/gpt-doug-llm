# GPT-Doug Brain Kernel

The gpt_brain package consolidates GPT-Doug's existing ontology, memory, provider, agent-chain and digital-clone concepts into one bounded orchestration kernel.

## Runtime loop

1. Recall episodic, semantic and procedural memory.
2. Ground the task against config/global-ontology.json.
3. Route to specialist agents: ontology, research, builder and critic.
4. Run specialists in parallel through the existing agents.llm_backend provider facade.
5. Run a critic pass over contradictions and unsupported claims.
6. Synthesize the final artifact with uncertainty and provenance.
7. Archive the outcome as an episodic record; secret-like material is rejected.

## Behavioral clone seeding

The brain can ingest an authorized text transcript or export into episodic memory.

Examples:

    gpt-doug-brain ingest-clone ./chat-export.txt --provenance "chat-export:2026-09-25"
    gpt-doug-brain run "build a medical cancer research ontology" --json
    gpt-doug-brain recall medical ontology cancer

This reproduces authorized context and behavior patterns. It does not copy proprietary model weights, inaccessible platform state, or hidden model reasoning.

## Existing components reused

- agents/llm_backend.py — provider-neutral model access
- config/global-ontology.json — ontology source of truth
- agents/agent_chain.py — bounded recursive agent-chain pattern
- doug_core/memory.py — append-only memory precedent
- gpt_chaos/digital_clone.py — digital-clone policy model

## Design-source mapping

The September 24 patent-search material supplied by the project owner includes architectural patterns such as task-specific mini-systems, entity/subentity model adaptation, real-time node-graph synchronization with LLM/RAG, prompt evolution, and a feedback-driven generative-AI brainstorming loop. These are treated as research/design references, not as proof of implementation or ownership.
