# GPT-Doug BioChip swarm (software prototype)

This is a **bounded, offline software simulation**, not a physical biochip, engineered neural tissue, or a self-replicating autonomous system. It builds on the existing BioPineal software research layer without accessing biological devices or networks.

## Run locally

```sh
python3 -m research_lab.biochip_swarm --workers 4 --cycles 3 --db /tmp/gpt-doug-biochip.sqlite3
python3 -m unittest tests.test_biochip_swarm
```

Python standard library only. The supervisor creates at most eight local threads, waits for each task, and exits; there is no automatic persistence as a background service, network communication, device actuation, or propagation to other computers. `--cycles` is capped at 100. Press Ctrl+C to interrupt. Treat `--db` as local sensitive state: choose a protected storage location and do not commit it.

## Core model

- **Brain:** existing GPT-Doug reasoning stack (not invoked by this proof-of-concept).
- **Memory:** local SQLite memory with content-hash deduplication.
- **Heartbeat:** per-worker, per-cycle audit events.
- **Swarm:** bounded, explicitly invoked local task replicas. No autonomous spawning.
- **Hardware bridge (future):** read-only sensor adapter, simulator-first validation, explicit access controls and separate review before real-world testing.

## Limits and readiness

This prototype uses synthetic health observations. It does not contain LLM inference, real biosensor readings, regulated biomedical verification, or hardware fabrication. A proposed biological interface would require its own scientific feasibility work, electrical/biocompatibility testing, and applicable safety/regulatory review. Do not treat the heartbeat records as evidence of a living neural system.

## Next engineering gates

1. Add structured read-only sensor inputs and schema validation.
2. Add configurable access controls, state retention and tamper-evident event export.
3. Connect the existing ontology under an explicit approved adapter.
4. Add resource telemetry and CI integration.
5. Test physical prototypes only after specialist review.
