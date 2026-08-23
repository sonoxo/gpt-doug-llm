# Adaptive Intelligence Cycle

GPT-DOUG-LLM can use a bounded, source-aware loop for research and agent orchestration:

1. **Absorb** — ingest explicit evidence with provenance and a caller-supplied reliability estimate.
2. **Index** — deduplicate equivalent evidence and rank it without treating official-sounding language as proof.
3. **Ideate** — build a compact, grounded context packet for a planner or language model. The packet separates evidence from inference.
4. **Verify** — require material claims to map back to known source IDs and return a confidence score derived from the mapped evidence.
5. **Reflect** — record explicit pass/fail outcomes for execution strategies so future strategy preference can adapt without changing source truth.

The implementation lives in `agents/adaptive_intelligence.py` and is intentionally model-independent. It does not fabricate intelligence, access restricted systems, or infer that a document is authoritative because it uses intelligence-community terminology.

## Source inspiration

This cycle was informed by concepts in the user-provided public document *The CIA Mental Edge Daily Routine* by Andrew Bustamante / EverydaySpy, especially its absorb/index/ideate/reflection framing. The implementation converts those concepts into software orchestration primitives; it is not presented as CIA software, classified methodology, or an official CIA system.

## Example

```python
from agents.adaptive_intelligence import AdaptiveIntel, Evidence

intel = AdaptiveIntel()
intel.absorb([
    Evidence(
        source_id="brief-1",
        text="A source-grounded observation.",
        provenance="user_document",
        reliability=0.7,
    )
])

packet = intel.ideate_packet("Evaluate the observation")
checks = intel.verify({"The observation exists": ["brief-1"]})
intel.record_outcome("planner-v1", passed=all(item.supported for item in checks))
print(packet)
print(intel.snapshot())
```

## Design constraints

- Evidence storage is bounded.
- Duplicate text keeps the stronger scored source.
- Unsupported claims receive zero confidence and are surfaced as issues.
- Strategy adaptation uses only explicit outcome feedback.
- Evidence reliability is never silently upgraded based on task success.
- The module is suitable for local/offline use and has no network dependency.

## Tests

Run:

```bash
python -m unittest agents.tests.test_adaptive_intelligence
```
