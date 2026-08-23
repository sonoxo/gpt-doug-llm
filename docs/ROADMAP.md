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

## Phase 2 — Mission Intelligence ✅

- [x] Structured JSONL mission event journal
- [x] Step-level timing and token/model-call telemetry
- [x] Better failure taxonomy: planning, tool, validation, review, runtime
- [x] DAG mission planner with dependency-aware steps
- [x] Mission resume from explicit checkpoints
- [x] Deterministic acceptance criteria generated before editing
- [x] Multi-file patch previews before keep/rollback

## Phase 3 — Capability Manifests ✅

- [x] Machine-readable capability manifest per agent/tool
- [x] Per-mission capability grants
- [x] Read-only vs write-enabled mission profiles
- [x] Explicit network capability boundary for approved integrations
- [x] Signed mission policy snapshot
- [x] Tamper-evident autonomous-change journal

## Phase 4 — Reproducible Build Sandbox ✅

- [x] Ephemeral sandbox for generated apps
- [x] Dependency lock verification
- [x] Automatic local preview for web apps
- [x] Port/process lifecycle manager
- [x] Golden-path smoke tests
- [x] Artifact manifest and provenance report

## Phase 5 — ZYRA Mission Console ✅

- [x] Web dashboard for live mission events
- [x] Plan visualization
- [x] File-diff viewer
- [x] Checkpoint/rollback controls
- [x] Agent/LASER/self-heal telemetry
- [x] Mission history and benchmark views

## Phase 6 — Reliability Benchmarks ✅

- [x] Curated autonomous coding benchmark suite
- [x] Repeatability tests across local models
- [x] Rollback correctness score
- [x] False-success tracking
- [x] Human-correction rate
- [x] Performance budget regression checks
- [x] Release scorecard

## Mission Control 1.0

The Phase 2–6 foundations are implemented in `zyra_control_plane/` and exposed
through `zyra_control.py`. The implementation is deliberately local-first and
bounded: capability grants are explicit, the console binds to localhost by
default, sandbox commands use an executable allowlist with `shell=False`, and
external delivery remains subject to the repository's existing human/CI gates.

See [ZYRA Mission Control](ZYRA_MISSION_CONTROL.md) for usage and architecture.

## Long-term direction

ZYRA should become more autonomous by becoming **better at planning, safer at execution, more observable during work, and easier to reverse when wrong**.

The project does not treat unrestricted system access as a maturity milestone.
