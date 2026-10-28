# GPT-DOUG Metacognition Bio-Chip Swarm

A bounded, model-agnostic scaffold for improving reasoning reliability through
specialized review roles. "Bio-chip" is an architecture metaphor here; this
package does not claim biological hardware, novel chips, unlimited tokens, or
autonomous model replication.

## Review loop

1. **Planner** decomposes the task and defines acceptance criteria.
2. **Critic** identifies assumptions, contradictions, and risks.
3. **Evidence auditor** checks provenance and evidence sufficiency.
4. **Verifier** defines reproducible tests.
5. **Policy gate** holds work that lacks evidence, authorization, or required tests.

The initial Python implementation scores review completeness only. It does not
establish factual truth, call an LLM, launch agents, or execute external actions.
Real model adapters must be added explicitly and tested independently.

## Safety and operating bounds

- Review rounds are bounded (default two; hard maximum five).
- Empty or unsupported candidates are held.
- No autonomous self-modifying code, credential access, deployment, or external
  side effects.
- Route execution through THEGREENHOUSE with least-privilege capabilities and
  append-only audit records.
- Keep model outputs untrusted until independently verified.
- Report confidence as a review signal, never as a guarantee of correctness.

## Run tests

From the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_metacognition_swarm.py'
```

## Integration status

This is an initial scaffold on a feature branch. It is not deployed, does not
connect to Foundry or Devin, and does not use live model APIs.
