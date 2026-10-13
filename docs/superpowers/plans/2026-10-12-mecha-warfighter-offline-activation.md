# MECHA Warfighter Offline Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a real, testable `scripts/doug-max mecha demo` and `mecha doctor` that run a synthetic, research-only inspection-rover MECHA with bounded classical quantum mathematics, truthful 6-channel status, provenance and optional read-only BioPINEAL integration.

**Architecture:** Make `mecha/` a portable Python package that works independently without GPT-Doug imports or paid/cloud APIs. Keep all GPT-Doug, Agent10, BioPINEAL, PINEAL, ZYRA, robotics, and guardrail integration in a separate lazy host-only bridge. The canonical package computes deterministic synthetic states, never sends motion commands, and makes no authenticated-military, quantum-hardware, biological-hardware or operational-readiness claims.

**Tech Stack:** Python 3.9+ standard library (`argparse`, `json`, `math`, `cmath`, `hashlib`, `pathlib`, `unittest`), current `scripts/doug-max` shell preflight, existing BioPINEAL and ZYRA/PINEAL read-only APIs where present. No mandatory Blender, numpy, robotics framework, internet, token, device driver or GPU.

**Spec:** `docs/superpowers/specs/2026-10-12-mecha-dual-repo-biopineal-design.md` (design PR #348). This is the **first execution slice** M0–M1 with a minimal terminal M2; separate distribution/Blender plan covers the rest.

## Global Constraints

- Default `RESEARCH_ONLY`, `SYNTHETIC` and `REAL_WORLD_ACTUATION=false`; no actual vehicle, weapon, sensor, military system, real robot or classified data connection.
- The project currently has unmerged draft dependencies: Warfighter PR #344, Agent10/BioPINEAL PR #345, public sources PR #346, research-freedom PR #347. Do **not** merge them by assumption. Host adapters must be optional and read-only, and tests must explicitly cover missing modules.
- A local operator callsign `Agent10` is unverified and private. Do not export it to public snapshots, GLB, logs or source control.
- The existing `scripts/doug-max` guardrail preflight remains intact; `mecha` is **not** inserted into the read-only preflight exemption, since some later subcommands may write local files.
- At most 64 KiB input, 1 MiB output, 200 scene nodes, 6 simulated qubits, 128 gates and 1,024 synthetic shots. No unbounded simulation, background heartbeat, auto-install, autonomous task dispatch or network access.
- Mitochondrial `compute_units` are integer operation-cost **analogies**, not biological ATP or measured energy. Classical amplitudes do not imply real quantum hardware.
- Portable package source lives inside `mecha/mecha/`; when run in monorepo, use `PYTHONPATH="$ROOT/mecha:$ROOT"`. The standalone mirror will use the same package directory but is **not created in this phase**.
- Existing ZYRA-MSS schema, PINEAL federation allowlist and XQE dispatch files must remain unchanged. The descriptive research-freedom policy never authorizes hardware or publication.
- Every task is test-first: focused RED, minimum GREEN implementation, regression run, small commit. No step authorizes merge of open dependency PRs.
- Any actual hardware integration, patent rights, biometric data, or deployment is separately scoped and reviewed; no safety/certification claims.

## Review Focus

1. **Private callsign leaks into exported JSON**: use a malicious fixture containing `Agent10` and government-identity fields; validator must reject them and public snapshot must contain no operator metadata (Tasks 1 and 3).
2. **Fixture attempts a real command**: fields such as `motor_command`, `endpoint`, `gps_route`, `target_coordinates` or `write_capability` must be rejected before simulation, not ignored (Tasks 1–2).
3. **Host module unavailable**: MECHA doctor/demo must still succeed offline in standalone mode, reporting `ADAPTER_UNAVAILABLE` rather than creating PINEAL DB or claiming LIVE access (Task 6).
4. **Malformed or unbounded quantum state**: invalid gate, seven-qubit request, excessive shots, nondeterministic sample or norm failure must fail with a bounded error (Task 4).
5. **Guardrail bypass via CLI routing or renderer input**: `scripts/doug-max mecha` must retain preflight, sanitize ANSI text and never dispatch XQE, import vehicle drivers or create a network socket (Tasks 5, 7 and 8).

---

## File Map

| Path | Purpose |
| --- | --- |
| `mecha/README.md`, `mecha/pyproject.toml` | Portable project and install metadata, version/rights/truth status |
| `mecha/mecha/__init__.py` | Package version; no side effects |
| `mecha/mecha/contracts.py` | Synthetic-only fixture/snapshot schema, limits, validation and hash helpers |
| `mecha/mecha/fixtures.py` | Confined local file loading, canonical digest |
| `mecha/mecha/robotics.py` | Toy inspection rover state and finite deterministic steps |
| `mecha/mecha/snapshot.py` | Immutable style, public-safe JSON object with six channels |
| `mecha/mecha/quantum.py` | Bounded pure classical statevector simulator; one MECHA implementation |
| `mecha/mecha/render/terminal.py` | Read-only finite ASCII rotating 3D projection |
| `mecha/mecha/cli.py` | Headless `doctor`, `demo`, `watch`, `quantum` commands |
| `mecha/examples/synthetic-inspection-rover.json` | Deterministic synthetic fixture with no operator identity |
| `mecha/examples/bell-state.json` | Two-qubit H+CNOT reference fixture |
| `mecha/tests/test_contracts.py` | Boundary, source/trust, injection and bad-field tests |
| `mecha/tests/test_robotics.py` | Finite toy rover deterministic state |
| `mecha/tests/test_snapshot.py` | Hash, data channel semantics, public-private separation |
| `mecha/tests/test_quantum.py` | Gate algebra, normalization and hard caps |
| `mecha/tests/test_terminal.py` | Read-only frame determinism, finite width and no ANSI injection |
| `mecha/tests/test_cli.py` | Standalone end-to-end offline app |
| `integrations/mecha_bridge/__init__.py` | Host-only package marker |
| `integrations/mecha_bridge/adapters.py` | Optional read-only BioPINEAL, callsign, ontology/rover contract adapters |
| `tests/test_mecha_bridge.py` | Host integration truth/privacy/absence tests |
| `tests/test_mecha_guarded_entry.py` | Existing guardrail preflight and shell integration |
| `scripts/doug-max` | Guarded `mecha` command route |
| `docs/MECHA.md` | Exact verified terminal instructions and scientific/license limits |
| `.github/workflows/mecha-research.yml` | Python 3.9/3.13 tests, shell syntax, no-governance-diff check |

### Task 1: Portable JSON Contracts and Safe Fixture Loading

**Files:** Create `mecha/pyproject.toml`, `mecha/mecha/__init__.py`, `mecha/mecha/contracts.py`, `mecha/mecha/fixtures.py`, `mecha/examples/synthetic-inspection-rover.json`, `mecha/tests/test_contracts.py`.

**Interfaces:** `canonical_json(value: Any) -> bytes`; `digest(value: Any) -> str`; `validate_fixture(payload: Mapping[str, Any]) -> dict[str, Any]`; `load_fixture(file: Path, *, input_root: Path) -> dict[str, Any]`.

Fixture key set: `schema_version`, `type`, `source_kind`, `authority`, `mode`, `synthetic`, `seed`, `robot`, `environment`, `assumptions`. Version `1.0.0`, type `MechaExercise`, source `SYNTHETIC`, authority `RESEARCH_ONLY`, mode `OFFLINE_ROBOTICS_DEMO`, synthetic exactly `true`, seed integer 0..2^32-1. Robot keys `id`, `class`, `pose`, `health_pct`, `power_budget_units`; class `INDUSTRIAL_INSPECTION_ROVER`; pose exactly three finite numbers each in [-100,100], health integer 0..100, power budget integer 1..1000000. Environment keys `terrain` and `obstacles`; terrain `SYNTHETIC_FLAT`, at most 50 obstacles with three finite coordinates each. Assumptions: 1..12 strings <=256 ASCII noncontrol characters. Unknown keys denied.

- [ ] **Step 1: Write failing `test_contracts.py`**: valid demo returns exact declared schema, stable SHA-256 independent of JSON key order; reject `classification="SECRET"`, `source_kind="LIVE"`, `operator="Agent10"`, `credential`, `motor_command`, `gps_route`, `target_coordinates`, `endpoint`, `write_capability`, seven extra nodes, bool used as integer, NaN/Infinity, oversized UTF-8 JSON, symlink path or parent traversal.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_contracts.py' -v`. Expected RED because portable contract/loader do not exist.
- [ ] **Step 3: Implement** APIs using strict schema and finite-value checks; 64 KiB input check before decode, reject symlink components and resolve only inside explicit `input_root`, canonical JSON with `allow_nan=False`. Reject unexpected input fields; do not attempt a network request.
- [ ] **Step 4: Run** the Task 1 test command; expected GREEN on both valid and hostile fixtures.
- [ ] **Step 5: Commit** `git add mecha/pyproject.toml mecha/mecha/__init__.py mecha/mecha/contracts.py mecha/mecha/fixtures.py mecha/examples/synthetic-inspection-rover.json mecha/tests/test_contracts.py && git commit -m "feat(mecha): strict synthetic contracts and fixture boundary"`.

### Task 2: Simulated Civilian Inspection Rover (No Actuation)

**Files:** Create `mecha/mecha/robotics.py` and `mecha/tests/test_robotics.py`.

**Interfaces:** `simulate_rover(fixture: dict[str, Any], *, steps: int = 3) -> dict[str, Any]`. For each step 1..20, advance *simulated* X by 0.25 units if no synthetic obstacle is within 0.5 model units at the candidate point, else halt in SIMULATED_OBSTACLE_HALT. Preserve Y,Z. Deduct one abstract power unit per accepted step. Output `simulated_pose`, `simulated_steps`, `simulated_power_remaining`, `sensor_health_pct`, `simulation_status` and `REAL_WORLD_ACTUATION=false`. Values are bounded hypothetical, not control instructions.

- [ ] **Step 1: Write failing `test_robotics.py`**: default 3 steps move synthetic X 0→0.75 and consume 3 model units; obstacle at X=0.25 halts before movement; budget 1 halts on exhaustion; invalid step count 0,21,True rejects; input unchanged; no output field named `motor_command`, `navigation_target`, `autopilot` or `execution_endpoint`.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_robotics.py' -v`. Expected RED.
- [ ] **Step 3: Implement** pure numeric stepping on the *validated* fixture. No robotic middleware, drivers, ROS, flight controls, robotics sockets or real GPS.
- [ ] **Step 4: Run** focused test; expected GREEN.
- [ ] **Step 5: Commit** `git add mecha/mecha/robotics.py mecha/tests/test_robotics.py && git commit -m "feat(mecha): deterministic offline industrial rover exercise"`.

### Task 3: Truthful Six-Channel Public Snapshot

**Files:** Create `mecha/mecha/snapshot.py` and `mecha/tests/test_snapshot.py`.

**Interfaces:** `build_snapshot(fixture: dict[str, Any], model_state: dict[str, Any], *, model_version: str = "1.0.0") -> dict[str, Any]`. Output keys include `schema_version="1.0.0"`, `type="MechaSnapshot"`, `system="GPT-DOUG-MECHA"`, `source_kind="SYNTHETIC"`, `authority="RESEARCH_ONLY"`, `mode="OFFLINE_ROBOTICS_DEMO"`, `real_world_actuation=false`, `quantum_hardware_used=false`, `biological_hardware_connected=false`, source fixture SHA-256 and six-channel labels `x/y/z/time/memory/compute`. Source hash is over the *canonical fixture bytes*. No operator field in this public contract.

- [ ] **Step 1: Write failing `test_snapshot.py`**: SHA-256 matches fixture; x/y/z actual synthetic coordinates; D4 time=simulation step (not measured clock); D5 memory=provenance labels only; D6 compute=abstract model operations; public JSON never contains Agent10, private absolute paths, tokens or live operational labels even with hostile model state. Verify 1 MiB cap and deterministic repeated serialization.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_snapshot.py' -v`. Expected RED.
- [ ] **Step 3: Implement** allowlisted copy-only construction and safe numeric output, never a generic dict dump of host telemetry or private profile.
- [ ] **Step 4: Run** focused tests; expected GREEN.
- [ ] **Step 5: Commit** `git add mecha/mecha/snapshot.py mecha/tests/test_snapshot.py && git commit -m "feat(mecha): public-safe six-channel snapshot and provenance"`.

### Task 4: Portable Bounded Classical Quantum Model

**Files:** Create `mecha/mecha/quantum.py`, `mecha/examples/bell-state.json` and `mecha/tests/test_quantum.py`.

**Interfaces:** `simulate_quantum(problem: Mapping[str, Any], *, budget_units: int = 200) -> dict[str, Any]`. Accept exactly keys `qubits`, `initial_basis`, `gates`, `shots`, `seed`. Gates H/X/Z/CNOT, <=6 qubits, <=128 gates, <=1024 shots; 32-bit seed, no extra or malformed fields. For n qubits, cost `compute_units_used = 2**n * (1 + len(gates)) + shots`; hard budget max 1,000,000. Return probabilities by fixed-width bitstrings, amplitude norm check within 1e-10, seeded sampled counts when shots>0, `classical_simulation=true` and `quantum_hardware_used=false`. Do not expose “entanglement hardware” or “quantum speedup”.

- [ ] **Step 1: Write failing `test_quantum.py`**: H(0),CNOT(0→1) on |00> yields 0.5 for 00 and 11 (within 1e-12) and 0 for 01,10; H twice restores |0>; Z changes phase but not outcome probability; identical seed/sample count produces identical frequencies; Bell demo uses 12 abstract units, reject 7 qubits, 129 gates, 1025 shots, fake unitary name, CNOT identical indices, invalid budget, NaN and output private fields.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_quantum.py' -v`. Expected RED.
- [ ] **Step 3: Implement** classical complex state vector and deterministic RNG. Canonical MECHA implementation stands alone; the host adapter may compare results with existing `research_lab.warfighter.biopineal.simulate_biomito_quantum`, but **must never copy/replace its code or silently substitute a different calculation**.
- [ ] **Step 4: Run** focused tests; expected GREEN, no optional dependencies.
- [ ] **Step 5: Commit** `git add mecha/mecha/quantum.py mecha/examples/bell-state.json mecha/tests/test_quantum.py && git commit -m "feat(mecha): bounded classical research quantum engine"`.

### Task 5: Read-Only Terminal Cortex

**Files:** Create `mecha/mecha/render/__init__.py`, `mecha/mecha/render/terminal.py`, `mecha/tests/test_terminal.py`.

**Interfaces:** `render_frame(snapshot: Mapping[str, Any], *, frame: int = 0, width: int = 80, color: bool = False) -> str`; `render_frames(snapshot: Mapping[str, Any], *, frames: int = 3, width: int = 80, color: bool = False) -> list[str]`. Display bounded ASCII wireframe projections (3 simulated coordinates) and six readable channel labels; width 40–160, frame count 1–1000, never a background loop without explicit CLI command.

- [ ] **Step 1: Write failing `test_terminal.py`**: frame 0 deterministic, frame 1 changes a rotation glyph, output includes `SYNTHETIC`, `RESEARCH_ONLY`, `MECHA`, `No real robotics connected`; no ESC control codes or malicious user-provided terminal-sequence injection; 0 frames, 1001 frames, width 10, 161 rejected; no CPU/GPU measurement fabricated.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_terminal.py' -v`. Expected RED.
- [ ] **Step 3: Implement** simple finite-frame rotating orthographic wireframe on sanitized snapshot only, clear labels and NO-SIGNAL fallback for missing data.
- [ ] **Step 4: Run** focused tests; expected GREEN without TTY or graphics dependencies.
- [ ] **Step 5: Commit** `git add mecha/mecha/render mecha/tests/test_terminal.py && git commit -m "feat(mecha): bounded read-only terminal cortex"`.

### Task 6: Portable Standalone CLI and Offline End-to-End Demo

**Files:** Create `mecha/mecha/cli.py`, `mecha/README.md` and `mecha/tests/test_cli.py`.

**Interfaces:** `main(argv: list[str] | None = None) -> int`. Subcommands:
- `doctor` => JSON with `implementation="SIMULATED_OFFLINE_V1"`, `authority="RESEARCH_ONLY"`, `connected_robot=false`, `real_world_actuation=false`, `external_calls=0`, plus clearly marked optional host adapters unavailable in standalone.
- `demo --fixture FILE --input-root ROOT [--steps 3]` => validated synthetic state and public snapshot JSON, no automatic file writes.
- `watch --fixture FILE --input-root ROOT --frames 3 --no-color` => finite ASCII frames; read-only and no daemon.
- `quantum FILE --input-root ROOT --budget-units 200` => deterministic classical probability output.

- [ ] **Step 1: Write failing `test_cli.py`**: `PYTHONPATH=mecha python3 -m mecha.cli doctor` works without GPT-Doug; repeat demo JSON identical; watch outputs exactly 3 finite frames; Bell sample gives 0.5/0.5; hostile fixture returns nonzero with JSON error, no work directory created and no network. Import must not read PINEAL DB or `agents`.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_cli.py' -v`. Expected RED.
- [ ] **Step 3: Implement** CLI as wrapper around Tasks 1–5; no shells, eval, dynamic script execution, provider API calls or implicit write. Document commands, expected status, licensing distinction and default-branch availability honestly.
- [ ] **Step 4: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_*.py' -v`. Expected GREEN across all portable tests.
- [ ] **Step 5: Commit** `git add mecha/mecha/cli.py mecha/README.md mecha/tests/test_cli.py && git commit -m "feat(mecha): portable offline inspection cortex CLI"`.

### Task 7: Optional GPT-Doug / BioPINEAL Host Bridge

**Files:** Create `integrations/mecha_bridge/__init__.py`, `integrations/mecha_bridge/adapters.py` and `tests/test_mecha_bridge.py`.

**Interfaces:** `host_status(*, memory_root: Path | None = None, operator_workspace: Path | None = None) -> dict[str, Any]`, `host_quantum_comparison(problem: Mapping[str,Any]) -> dict[str,Any]`. Both use guarded, lazy imports. Status may read current heartbeat and self-declared callsign (private terminal only), ZYRA schema presence and rover connector template, but cannot write PINEAL or dispatch a real command. Fallback returns `ADAPTER_UNAVAILABLE` per subsystem. Quantum comparison reports numeric mismatch rather than claiming independent validation when BioPINEAL unavailable or differs.

- [ ] **Step 1: Write failing `test_mecha_bridge.py`**: when Warfighter/Agent10 modules missing, host bridge returns honest unavailable status and `mecha.cli demo` still passes; present public source does not contain callsign, host path or content of PINEAL notes; heartbeat 250s old is STALE; rover contract says `command_write=false`; custom input cannot cause PINEAL DB creation, XQE task dispatch, network socket or privileged operator elevation; Bell equivalence check succeeds only when actual module is present.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest tests.test_mecha_bridge -v`. Expected RED.
- [ ] **Step 3: Implement** read-only adapter with strict source-field picking, no eager or import-time IO, and no wide exception masking of incorrect claims. Host-private session status and public snapshot remain separate types. Never use the descriptive `research_freedom.evaluate` output as permission to perform actions.
- [ ] **Step 4: Run** focused test and `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_*.py' -q`; expected GREEN.
- [ ] **Step 5: Commit** `git add integrations/mecha_bridge tests/test_mecha_bridge.py && git commit -m "feat(mecha): host-only read-only BioPINEAL and rover adapters"`.

### Task 8: Guarded GPT-Doug Launcher + CI + User Documentation

**Files:** Modify `scripts/doug-max`, create `tests/test_mecha_guarded_entry.py`, `docs/MECHA.md` and `.github/workflows/mecha-research.yml`.

**Interfaces:** add `mecha) shift; cd "$ROOT"; exec env PYTHONPATH="$ROOT/mecha:$ROOT..." python3 -m mecha.cli "$@" ;;` as a *normal guarded* branch. Do **not** add `mecha` to the `read_only_mode` allowlist, to preserve preflight. Add `doctor`, `demo`, `watch` and `quantum` tests through the actual launcher.

- [ ] **Step 1: Write failing `test_mecha_guarded_entry.py`** asserting `bash -n scripts/doug-max` succeeds, `bash scripts/doug-max mecha doctor` emits research-only JSON, guardrail validator remains in preflight for `mecha`, no "mecha" unconditional bypass, and negative robot/quantum fixtures do not invoke XQE/network. Enforce unchanged existing `safety-shield/ontology/zyra-mss-v1.json`, `integrations/gpt-doug-pineal/src/pineal/federation.py` and `workers/xqe.py`.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest tests.test_mecha_guarded_entry -v`. Expected RED because wrapper route does not exist; run `bash -n scripts/doug-max` to baseline current shell syntax.
- [ ] **Step 3: Implement** minimal `mecha` routing without relaxing current preflight. Add CI matrix Python 3.9/3.13 checking portable tests, guarded end-to-end, Warfighter integration when available, shell syntax, no-governance-diff, input-boundary negatives. Create `docs/MECHA.md` with commands and explicit no-physical-MECHA claims.
- [ ] **Step 4: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_*.py' -v`, `PYTHONPATH=mecha:. python3 -m unittest tests.test_mecha_bridge tests.test_mecha_guarded_entry -v`, `bash -n scripts/doug-max`, `bash scripts/doug-max mecha doctor`, `python3 -m pytest -q tests/test_gpt_doug_max_robotics_lab.py` (if pytest installed), and the existing research Warfighter/BioPINEAL/ZYRA/PINEAL regression suites when available. Expected no new failures, with existing unrelated regressions reported separately.
- [ ] **Step 5: Commit** `git add scripts/doug-max tests/test_mecha_guarded_entry.py docs/MECHA.md .github/workflows/mecha-research.yml && git commit -m "feat(mecha): gated Warfighter MECHA terminal activation"`.

## End-to-End Release Gate and Handoff

- First usable command after code exists, **not before**: `bash scripts/doug-max mecha doctor` and `bash scripts/doug-max mecha demo --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples`.
- Require independent security/code review and green full-repository checks; open a draft PR first, and **do not auto-merge** it into `main`. A Python test in a local sandbox is not proof of a runnable robotics appliance.
- Existing draft PRs #344–#347 must remain reviewable; if the hosted bridge depends on changes not merged, mark those adapter tests conditional and list precise prerequisites rather than adding broad automatic patching.
- The portable package is designed to run in the later standalone `sonoxo/mecha` repository with exactly the same artifacts. However no standalone repository, Blender scene or 10D/11D runtime is claimed from this slice.
- The companion plan `docs/superpowers/plans/2026-10-12-mecha-visualization-and-distribution.md` covers Blender/geometry and the second repository; these do not block a verified offline M0 core.
- Do not begin implementation until the user reviews this plan. If independent subagents are unavailable, disclose this and use native TDD with an external/independent PR review rather than pretending separate workers ran.
