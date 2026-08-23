# Cognitive Analyst Core

`agents/cognitive_analyst_core.py` gives GPT-DOUG-LLM an explicit, bounded operational self-model for agentic analysis. It is not a claim of sentience, human consciousness, CIA/FBI affiliation, or government authority.

## Design sources

The architecture combines public analytic ideas rather than copying a secret system:

- The FBI's public intelligence cycle: requirements; planning and direction; collection; processing and exploitation; analysis and production; dissemination.
- CIA public structured analytic tradecraft: assumptions checks, multiple hypotheses, challenging conventional wisdom, and explicit attention to information gaps.
- ODNI ICD 203 public analytic standards: source credibility, uncertainty, separation of information from assumptions/judgments, analysis of alternatives, clear logic, and explaining changes in judgments.
- The user-provided *CIA Mental Edge Daily Routine* framing around absorb/index/ideate/reflection is represented in the existing `adaptive_intelligence.py` layer.

## What "agentic cognition" means here

The system maintains a machine-readable self-model containing:

- identity/name and mission
- current intelligence-cycle phase
- operating principles and limits
- bounded working observations with provenance and reliability
- explicit observations, inferences, hypotheses, and recommendations
- unknowns and information gaps
- confidence-capped judgments
- decision gates for consequential actions
- strategy success/failure statistics
- a bounded reflection log

This gives the agent continuity and metacognitive structure without pretending it has subjective experience.

## Core cycle

1. `set_requirements()` — define objective and constraints.
2. `plan_collection()` — identify questions to answer, restricted to authorized inputs and tools.
3. `collect()` — ingest source-tagged observations.
4. `process()` — normalize, deduplicate, and rank evidence.
5. `analysis_packet()` — create a source-grounded packet that requires assumptions, alternatives, information gaps, confidence, and disconfirming evidence.
6. `commit_judgment()` — store a typed judgment; unsupported inference/hypothesis confidence is automatically capped.
7. `gate_action()` — block high-consequence actions when evidence is weak or the action is irreversible.
8. `disseminate()` — produce an audience-aware judgment packet with sources, confidence, and unknowns.
9. `reflect()` — update strategy preferences from explicit outcomes.

## Safety and integrity properties

- No hidden collection. Inputs must be supplied by authorized callers.
- No new system permissions are created by this module.
- An official-sounding source name cannot raise evidence reliability automatically.
- Unsupported observations cannot be committed as facts.
- Unsupported inference/hypothesis confidence is capped.
- High-consequence irreversible actions are blocked by the local decision gate.
- Strategy learning changes process preference, not source truth.
- Reflection is bounded; it does not recursively rewrite its own source code.

## Example

```python
from agents.cognitive_analyst_core import CognitiveAnalystCore, Observation, ClaimKind

core = CognitiveAnalystCore(name="GPT-DOUG-LLM")
core.set_requirements("Assess whether a proposed change is ready to ship", ["use repository evidence"])
core.plan_collection(["What tests passed?", "What changed?", "What remains unknown?"])
core.collect([
    Observation("ci-1", "Unit tests passed", reliability=0.95, provenance="github_actions"),
])

packet = core.analysis_packet("Is the change ready to ship?")
judgment = core.commit_judgment(
    "Unit-level evidence supports the change",
    ClaimKind.INFERENCE,
    ["ci-1"],
    confidence=0.8,
)

gate = core.gate_action(
    "merge pull request",
    ["ci-1"],
    reversible=True,
    consequence="external",
)
print(packet)
print(judgment)
print(gate)
```

## Tests

Run:

```bash
python -m unittest agents.tests.test_cognitive_analyst_core
```
