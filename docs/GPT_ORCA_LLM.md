# GPT-Orca-LLM

A bounded, ontology-first multi-role research council for GPT-Doug-LLM.
It is **not AGI**, does not train new model weights or reproduce itself, and
does not independently access external systems.

## Roles
1. Planner — draft a testable approach.
2. Researcher — reason over supplied evidence.
3. Critic — challenge unsupported assertions.
4. Synthesizer — produce an evidence-aware result.

Uses existing `agents.llm_backend_free.chat_once` so provider selection and
the `PAID_MODE` guard remain authoritative. Evidence is indexed through
`AdaptiveIntel`, preserving source IDs and provenance. All role output is
untrusted and remains in bounded memory for the current request.

## Usage

```bash
python -m agents.gpt_orca_llm "Analyze this engineering proposal"
python -m agents.gpt_orca_llm "Evaluate the evidence" --evidence-json ./sources.json
python -m unittest agents.tests.test_gpt_orca_llm -v
```

Evidence JSON:
```json
[{"source_id":"note-1","text":"A verifiable statement","provenance":"user","reliability":0.8}]
```

The tool does not validate model assertions automatically: users should verify
claims against the cited source material. Failure to configure a provider returns
an incomplete result rather than silently claiming an answer.
