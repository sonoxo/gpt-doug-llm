# GoDsEye Core, API, and CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the shared GoDsEye fusion core, planetary planning adapter, read-only API, and stable gpt-doug command surface.

**Architecture:** Add a focused godseye package that normalizes existing subsystem state without bypassing policy, then expose that package through FastAPI and the existing CLI. Keep all real-world action paths outside GoDsEye and make every subsystem failure degrade independently instead of collapsing the full snapshot.

**Tech Stack:** Python 3.9+, dataclasses/typing, FastAPI, Pydantic, pytest, existing GPT-Doug Brain, WarHawk, and agency_cloud modules.

**Spec:** docs/superpowers/specs/2026-10-07-gpt-doug-planetary-godseye-design.md

## Global Constraints

- Authorized/public data, defensive analysis, software engineering, compliance, readiness, research, and simulation only.
- No private Pentagon/DoD access claims.
- Block autonomous target selection, weapons release, weapon/drone swarm control, hostile engagement, critical-infrastructure disruption, hack-back, credential theft, unattended real-world vehicle control, implant control, destructive biological or cyber actuation, and bypassing human authorization.
- Govern external messaging, access-policy changes, readiness-state changes, software promotion, and real-world equipment actions behind human review.
- GoDsEye is an observer/fusion layer, not a new source of authority.
- One degraded subsystem must yield a partial snapshot with explicit uncertainty, not a total failure.
- The CLI must work without requiring a system-wide editable pip install.

## Review Focus

- Malformed subsystem data must degrade only that subsystem.
- Blocked/private-control queries must be denied before any model call.
- External-capability claims without provenance must fail closed.
- Missing XUNIA planet wrapper must produce DEGRADED planetary state rather than an exception.
- PEP 668 must not prevent repo-local CLI execution.

---

### Task 1: Policy and typed state model

**Files:**
- Create: godseye/__init__.py
- Create: godseye/models.py
- Create: godseye/policy.py
- Modify: pyproject.toml
- Test: tests/test_godseye_policy.py
- Test: tests/test_godseye_models.py

**Interfaces:**
- Produces PolicyDecision(decision: str, matched: list[str], reason: str)
- Produces evaluate_request(text: str) -> PolicyDecision
- Produces SubsystemState(name, status, generated_at, source_count, stale, partial, provenance, errors, payload)
- Produces GoDsEyeSnapshot(schema, generated_at, policy, subsystems, provenance, uncertainty)
- Produces GoDsEyeSnapshot.to_dict() -> dict

- [ ] Step 1: Write failing policy tests for autonomous target selection, implant control, hack back, and a safe read-only query.
- [ ] Step 2: Run pytest tests/test_godseye_policy.py -v and confirm failure because the module is absent.
- [ ] Step 3: Implement deterministic evaluate_request with the spec BLOCK list and ALLOW_READ_ONLY fallback.
- [ ] Step 4: Write failing model tests proving to_dict preserves status, stale, partial, errors, provenance, and payload.
- [ ] Step 5: Run pytest tests/test_godseye_models.py -v and confirm failure.
- [ ] Step 6: Implement dataclasses, exports, and add godseye to the setuptools package list.
- [ ] Step 7: Run pytest tests/test_godseye_policy.py tests/test_godseye_models.py -v; expected PASS.
- [ ] Step 8: Commit: git add godseye pyproject.toml tests/test_godseye_policy.py tests/test_godseye_models.py && git commit -m "feat: add godseye policy and state models"

### Task 2: Planetary adapter and bounded planner

**Files:**
- Create: godseye/planetary.py
- Test: tests/test_godseye_planetary.py

**Interfaces:**
- Consumes docs/planet/index.html, agency_cloud.platform.SOURCE_REGISTRY, and WarHawkSwarm.plan.
- Produces planetary_status(*, planet_path=None, source_registry=None) -> dict
- Produces planetary_layers(status: dict) -> list[dict]
- Produces planetary_plan(mission: str, *, warhawk_factory=WarHawkSwarm, status_fn=planetary_status) -> dict

- [ ] Step 1: Write failing status tests asserting schema gpt-doug.planetary-status.v1, ONLINE with the real wrapper, and DEGRADED with a missing wrapper.
- [ ] Step 2: Run the two tests and confirm failure.
- [ ] Step 3: Implement status/layer normalization without remote scraping or browser geolocation.
- [ ] Step 4: Write a failing planner test using an injected fake WarHawk factory; assert schema gpt-doug.planetary-plan.v1 and dry-run WarHawk output.
- [ ] Step 5: Run the planner test and confirm failure.
- [ ] Step 6: Implement planetary_plan; reject empty missions and never call WarHawkSwarm.run.
- [ ] Step 7: Run pytest tests/test_godseye_planetary.py -v; expected PASS.
- [ ] Step 8: Commit the planetary adapter and tests.

### Task 3: Fusion snapshot and degradation isolation

**Files:**
- Create: godseye/fusion.py
- Test: tests/test_godseye_fusion.py

**Interfaces:**
- Consumes gpt_brain.status.build_status, WarHawkSwarm.status, global_intel_benchmark, global_posture, bioinformatics_fusion, and planetary_status.
- Produces collect_snapshot(*, settings=None, brain_status_fn=build_status, warhawk_factory=WarHawkSwarm, intel_fn=global_intel_benchmark, compliance_fn=global_posture, bio_fn=bioinformatics_fusion, planetary_fn=planetary_status) -> GoDsEyeSnapshot
- Produces snapshot_sources(snapshot: GoDsEyeSnapshot) -> list[dict]

- [ ] Step 1: Write a failing happy-path test requiring brain, warhawk, global_intel, global_compliance, biofusion, and planetary subsystem keys.
- [ ] Step 2: Run it and confirm failure.
- [ ] Step 3: Implement subsystem normalizers and preserve original payloads.
- [ ] Step 4: Add failing tests for TimeoutError and non-dict adapter responses; healthy subsystems must remain present.
- [ ] Step 5: Run degradation tests and confirm failure.
- [ ] Step 6: Implement per-subsystem exception isolation and explicit uncertainty.
- [ ] Step 7: Run pytest tests/test_godseye_fusion.py -v; expected PASS.
- [ ] Step 8: Commit the fusion snapshot and tests.

### Task 4: Provenance-aware query engine

**Files:**
- Create: godseye/query.py
- Test: tests/test_godseye_query.py

**Interfaces:**
- Consumes collect_snapshot, evaluate_request, and BrainKernel.run.
- Produces GoDsEyeQueryEngine(snapshot_fn=collect_snapshot, kernel_factory=BrainKernel)
- Produces GoDsEyeQueryEngine.query(question: str) -> dict

- [ ] Step 1: Write a failing read-only query test using fake snapshot and fake BrainKernel; require schema gpt-doug.godseye-query.v1, answer, provenance, uncertainty, and policy decision.
- [ ] Step 2: Run it and confirm failure.
- [ ] Step 3: Implement policy-first query composition with one BrainKernel.run call.
- [ ] Step 4: Add failing tests proving blocked requests never call the kernel and unverified private-control claims fail closed.
- [ ] Step 5: Run those tests and confirm failure.
- [ ] Step 6: Implement deterministic capability-claim validation without exposing hidden reasoning.
- [ ] Step 7: Run pytest tests/test_godseye_query.py -v; expected PASS.
- [ ] Step 8: Commit query engine and tests.

### Task 5: FastAPI routes

**Files:**
- Modify: agency_cloud/app.py
- Test: agency_cloud/tests/test_godseye_api.py

**Interfaces:**
- Add request model GoDsEyeQueryRequest(question: str, min 1, max 4000).
- Add request model PlanetaryPlanRequest(mission: str, min 1, max 4000).
- Add GET /api/v1/godseye/status
- Add POST /api/v1/godseye/query
- Add GET /api/v1/godseye/sources
- Add GET /api/v1/planetary/status
- Add POST /api/v1/planetary/plan
- Add GET /api/v1/planetary/layers

- [ ] Step 1: Write failing TestClient tests for all six routes and 422 validation for empty bodies.
- [ ] Step 2: Run pytest agency_cloud/tests/test_godseye_api.py -v; expected FAIL.
- [ ] Step 3: Implement thin route handlers using the GoDsEye interfaces.
- [ ] Step 4: Add a failing policy-denied API test expecting HTTP 403.
- [ ] Step 5: Run that test and confirm failure.
- [ ] Step 6: Translate blocked policy results to 403 and unexpected subsystem errors to generic 503 responses.
- [ ] Step 7: Run the API test file; expected PASS.
- [ ] Step 8: Commit app route changes and tests.

### Task 6: CLI and repo-local launcher

**Files:**
- Modify: gpt_brain/cli.py
- Create: scripts/gpt-doug-local
- Test: tests/test_godseye_cli.py
- Test: tests/test_gpt_doug_local_launcher.py

**Interfaces:**
- Add gpt-doug godseye status
- Add gpt-doug godseye query QUESTION
- Add gpt-doug godseye sources
- Add gpt-doug planetary status
- Add gpt-doug planetary plan MISSION
- Add gpt-doug planetary layers
- Launcher priority: project .venv/bin/python, then python3 -m gpt_brain.cli from repo root, else error 127.

- [ ] Step 1: Write failing parser/dispatch tests for all new commands.
- [ ] Step 2: Run pytest tests/test_godseye_cli.py -v; expected FAIL.
- [ ] Step 3: Implement subparsers and dispatch following the WarHawk pattern.
- [ ] Step 4: Write failing launcher tests that explicitly prove no pip install -e invocation occurs.
- [ ] Step 5: Run pytest tests/test_gpt_doug_local_launcher.py -v; expected FAIL.
- [ ] Step 6: Implement POSIX launcher with repo-root resolution.
- [ ] Step 7: Run both test files and sh -n scripts/gpt-doug-local; expected PASS/exit 0.
- [ ] Step 8: Commit CLI and launcher changes.

### Task 7: Core regression gate

**Files:** no new files unless a touched-file regression is found.

- [ ] Step 1: Run targeted regressions:

    pytest tests/test_warhawk_swarm.py tests/test_warhawk_cli.py tests/test_godseye_policy.py tests/test_godseye_models.py tests/test_godseye_planetary.py tests/test_godseye_fusion.py tests/test_godseye_query.py tests/test_godseye_cli.py tests/test_gpt_doug_local_launcher.py agency_cloud/tests/test_godseye_api.py agency_cloud/tests/test_service.py -v

Expected: all selected tests PASS.

- [ ] Step 2: Run python3 -m compileall godseye gpt_brain agency_cloud and sh -n scripts/gpt-doug-local; expected exit 0.
- [ ] Step 3: Commit only if a regression correction was necessary.
