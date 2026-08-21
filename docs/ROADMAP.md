# ZYRA Roadmap

This roadmap favors reliability, observability, and useful autonomous execution over unbounded capability growth.

## Phase 1 — Local Agentic Runtime ✅

- [x] Interactive ZYRA terminal
- [x] Ollama/local-provider runtime
- [x] Runtime self-heal
- [x] Native LASER defensive circuit breaker
- [x] Planner / executor / reviewer orchestration
- [x] Bounded Agent Core
- [x] Repository-scoped file tools
- [x] Checkpoint + rollback path
- [x] Native Agent Core self-test
- [x] Native LASER self-test
- [x] CI security gate

## Phase 2 — Mission Intelligence

- [ ] Structured JSONL mission event journal
- [ ] Step-level timing and token/model-call telemetry
- [ ] Better failure taxonomy: planning, tool, validation, review, runtime
- [ ] DAG mission planner with dependency-aware steps
- [ ] Mission resume from explicit checkpoints
- [ ] Deterministic acceptance criteria generated before editing
- [ ] Multi-file patch previews before keep/rollback

## Phase 3 — Capability Manifests

- [ ] Machine-readable capability manifest per agent/tool
- [ ] Per-mission capability grants
- [ ] Read-only vs write-enabled mission profiles
- [ ] Explicit network capability boundary for approved integrations
- [ ] Signed mission policy snapshot
- [ ] Tamper-evident autonomous-change journal

## Phase 4 — Reproducible Build Sandbox

- [ ] Ephemeral sandbox for generated apps
- [ ] Dependency lock verification
- [ ] Automatic local preview for web apps
- [ ] Port/process lifecycle manager
- [ ] Golden-path smoke tests
- [ ] Artifact manifest and provenance report

## Phase 5 — ZYRA Mission Console

- [ ] Web dashboard for live mission events
- [ ] Plan visualization
- [ ] File-diff viewer
- [ ] Checkpoint/rollback controls
- [ ] Agent/LASER/self-heal telemetry
- [ ] Mission history and benchmark views

## Phase 6 — Reliability Benchmarks

- [ ] Curated autonomous coding benchmark suite
- [ ] Repeatability tests across local models
- [ ] Rollback correctness score
- [ ] False-success tracking
- [ ] Human-correction rate
- [ ] Performance budget regression checks
- [ ] Release scorecard

## Long-term direction

ZYRA should become more autonomous by becoming **better at planning, safer at execution, more observable during work, and easier to reverse when wrong**.

The project does not treat unrestricted system access as a maturity milestone.
