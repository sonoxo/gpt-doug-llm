# US Patent 12,737,161 — generalized architecture notes

Reference: **US Patent 12,737,161**, *Robotic process automation acceleration and control*, patent date **2026-09-15**, inventor **Carolyn Jones**, assignee **The Huntington National Bank**.

GPT-Doug/GPT-Chaos use this document only as a source-grounded architecture reference. The repository implementation is independent and generalized; it does not copy claim language into executable behavior and does not assert non-infringement or ownership of the referenced patent.

## Generalized pattern adopted

```text
PIPELINE EVENTS
  -> NORMALIZE
  -> AUTOMATION COMPOSITES
  -> HISTORY / OUTCOME AGGREGATION
  -> BOUNDED RULE INDUCTION
  -> AUTOMATION-TYPE TEMPLATE
  -> NON-EXECUTABLE SETUP OBJECT
  -> DETERMINISTIC VALIDATION / AUTHORIZATION
  -> EXECUTION BY EXISTING RUNTIME
  -> OUTCOME TELEMETRY
  -> FEEDBACK LOOP
```

The implementation keeps the existing GPT-Doug rule:

```text
AGENTS PROPOSE -> VALIDATORS APPROVE -> EXECUTORS ACT -> CRITICS VERIFY
```

## Repository mapping

- `universal_hive/acceleration.py`
  - records pipeline outcomes;
  - deduplicates reusable automation composites;
  - derives evidence-bound stage statistics and preferred integrations;
  - generates automation-type templates;
  - emits non-executable setup objects with provenance.
- `hivemind/orchestrator.py`
  - exposes the learned template in plan metadata;
  - records executed Hivemind results into the adaptive loop;
  - never mutates learning state during a normal dry-run.
- `hivemind/cli.py`
  - exposes acceleration status, learned templates, and setup-object generation.

## Hard boundaries

- No generated code is automatically executed.
- No learned rule widens permissions.
- No learned rule bypasses ZYRA, authorization, compliance, or rollback requirements.
- Dry-run stays non-mutating.
- External actions continue to require the existing deterministic authorization path.
- The loop records observations and recommendations; it does not silently declare model-generated hypotheses to be facts.
