# GPT-Doug Quantum Lens and Higher-Dimensional Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scientifically honest, offline-first, visually ambitious “Quantum Lens” to the Warfighter Research Core: a small classical quantum-state demonstrator, bounded 6D/10D/11D geometry, a 3D-projected rotating terminal cortex, and optional editable Blender exports.

**Architecture:** The Lens is a separate **research-only** package consuming validated, synthetic exercise artifacts from the Warfighter Core. Pure classical mathematics produces reproducible numbers and projection metadata; renderers consume snapshots **read-only**. No renderer, simulation or display can publish findings, change ontology, contact external services or create operational commands.

**Tech Stack:** Python 3.9+ stdlib (`math`, `cmath`, `random`, `json`, `hashlib`, `argparse`, `unittest`); Blender 4.x with bundled `bpy` *optional*, no pip installation required for terminal/JSON. Apple Silicon 8 GiB RAM is the default lightweight target; no quantum hardware or paid tokens.

**Spec:** `docs/superpowers/specs/2026-10-12-quantum-warfighter-ontology-design.md`, especially ``7.3–7.5, 11, 14, 15, 17–18`. **Prerequisite:** the core interfaces from `docs/superpowers/plans/2026-10-12-warfighter-research-core.md` have landed and passed tests. This plan does not modify the separate `integrations/gpt-doug-pineal` Biochip 6D design.

## Global Constraints

- The Lens is **classical simulation** of small quantum mathematical systems, not a quantum processor, quantum supremacy, entanglement device, access to dimensions, new physical theory, weapons model or live military sensor.
- No physical six-dimensional spatial environment is generated: 6D = projected abstract state, 10D/11D = toy mathematical coordinate spaces sampled and projected into 3D. Display colors/pulses/rotation are presentation, not empirical readings.
- Quantum-state prototype: <=6 simulated qubits, <=128 declared gate operations, <=1024 measurement shots, default <=30 seconds per bounded run; independently record normalizations and numerical tolerances.
- Higher-D prototype: allowed 6, 10, 11 ambient dimensions; <=256 input sample points per toy object and <=1000 projected vertices; reject nonfinite values, malformed projection matrices, invalid radii, excessive mesh.
- Renderers accept **only sanitized** research results/synthetic examples. Default mode never ingests personnel, targeting, live location, operational telemetry or private PINEAL memory text.
- Terminal viewer needs no GPU, graphics app, paid API or network. Blender generator optional; absence must not prevent CLI math analysis.
- No dynamic script evaluation from input, arbitrary shell command, file system crawling, background start, automatic model download, opacity about status, or changes to ZYRA/PINEAL authority.
- Existing Warfighter research findings remain approved/unapproved per the Research Core; visualizing an artifact cannot change review or publication state.
- Tests use offline unit tests; Blender smoke tests run only where explicitly installed.

## Review Focus

1. **Nonunitary and malformed gates** must fail at validation, not silently renormalize into false proof (`test_statevector.py`).
2. **Sampling vs exact probabilities** must be distinguished and reproducible across seeds (`test_statevector.py`).
3. **Dimension confusion and noninvertible projection** must be explicitly labeled; 3D visual loss is unavoidable (`test_geometry_nd.py`).
4. **Terminal/BPY input injection** including ANSI escape strings, shader labels and hidden credentials must not appear in rendered/exported output (`test_lens_terminal.py`, `test_snapshot.py`).
5. **Headless/missing Blender** must produce an actionable optional-dependency error without loss of JSON/terminal functionality, attempts to install packages, or mutation of the existing PINEAL CAD outputs (`test_blender_export.py`).

---

## Feature Experience

The user selects an independently testable *lens*, not an imaginary capability upgrade:

| Lens mode | Source of truth | Visual language | Claim limit |
| --- | --- | --- | --- |
| **Hilbert Halo** | Existing exact-rational Bio-Hilbert research artifact | Six named channels projected as rotating orbit nodes with a decaying energy ring | Toy dynamics only |
| **Statevector Constellation** | Bounded classical simulation of <=6 qubits | 2^n amplitude stars, phase hue and probability radius | No quantum hardware or speedup |
| **Compactification Loom** | Deterministic 6D/10D/11D mathematical coordinates | Periodic coils/torus samples projected to 3D, with explicit rank-loss warnings | No experimentally validated extra dimensions |
| **Provenance Spine** | Approved/revoked research-only journal states | Linked evidence nodes with visible source/review tags | Project research authority only |
| **Biochip Cortex** | Optional current GPT-Doug heartbeat health and read-only PINEAL status | 3D circuit/heart analog with LIVE, STALE, MISSING labels | Software health metaphor, no biological chip |

For the first delivery, only the first three modes and a minimal research status legend are required; the full Biochip Cortex depends on its separately reviewed PINEAL visualization implementation.

## File Map

| Path | Responsibility |
| --- | --- |
| `research_lab/warfighter/quantum_inspired.py` | Pure statevector mathematical engine |
| `research_lab/warfighter/geometry_nd.py` | Finite-dimensional toy geometry + explicit projection |
| `research_lab/warfighter/lens_snapshot.py` | Deterministic sanitized read-only data envelope |
| `research_lab/warfighter/lens_terminal.py` | ANSI/ASCII renderer and finite-frame animation |
| `research_lab/warfighter/lens_cli.py` | Subcommands simulate, geometry, watch, export; optional Blender process |
| `research_lab/warfighter/blender_lens.py` | Standalone bpy script executed by installed Blender |
| `research_lab/warfighter/examples/statevector_hadamard.json` | Fixed input and seed |
| `research_lab/warfighter/examples/geometry_10d_torus.json` | Deterministic toy 10D example |
| `research_lab/warfighter/tests/test_statevector.py` | Matrix/gate/probability/limit checks |
| `research_lab/warfighter/tests/test_geometry_nd.py` | Dimension/rank/finite-value cases |
| `research_lab/warfighter/tests/test_snapshot.py` | Source-kind/privacy/status/integrity |
| `research_lab/warfighter/tests/test_lens_terminal.py` | Projection/frames/TTY/escaping |
| `research_lab/warfighter/tests/test_blender_export.py` | Optional executable detection, manifest, nonmutation |
| `docs/WARFIGHTER_QUANTUM_LENS.md` | Truthful instructions, examples, screenshots generated only from actual code |
| `research_lab/warfighter/cli.py` | Delegate `lens` subcommand to optional lens_cli while preserving core parser |
| `scripts/doug-max` | Use existing guarded `warfighter` dispatch, no new bypass |

### Task 1: Bounded Classical Quantum-State Mathematics

**Files:** Create `research_lab/warfighter/quantum_inspired.py`, `research_lab/warfighter/examples/statevector_hadamard.json`, `research_lab/warfighter/tests/test_statevector.py`.

**Interfaces:** `validate_quantum_problem(problem: Any) -> dict[str, Any]` and `simulate_quantum(problem: dict[str, Any]) -> dict[str, Any]`. Problem schema: `{"qubits":int,"initial_basis":int,"gates":list[dict],"shots":int,"seed":int}`; allowed gate names H, X, Z, CNOT; single-qubit gate targets and distinct CNOT control/target within qubit range. Deterministic reference fixture: one qubit, H on qubit 0 from |0>, 0 shots, seed 0. Exact expected probabilities 0.5/0.5 within 1e-12.

- [ ] **Step 1: Write failing tests**: H|0> has 0.5/0.5 probabilities; H twice restores |0> up to 1e-12; CNOT on control |1> flips target; phase-sensitive Z preserves magnitudes; reject >=7 qubits, >=129 gates, >1024 shots, nonunitary/malformed gate, duplicate/out-of-range CNOT indices, NaN amplitudes, negative seed; deterministic sampling for seed 0.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_statevector -v`. Expected RED.
- [ ] **Step 3: Implement** bounded 2^n complex amplitudes, gate operations and normalization check `abs(sum(abs(a)**2)-1)<=1e-10`; never invent hardware execution. Separate exact floating-point-computed probabilities from seed-based sampled frequency results; store qubit count, tolerances, max gate/shot limits, seed, algorithm revision, `classical_simulation=true`.
- [ ] **Step 4: Run** focused test. Expected GREEN; canonical repeated output stable.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/quantum_inspired.py research_lab/warfighter/examples/statevector_hadamard.json research_lab/warfighter/tests/test_statevector.py && git commit -m "feat(warfighter): classical six-qubit statevector demonstrator"`.

### Task 2: 6D/10D/11D Geometry and Honest Projection

**Files:** Create `research_lab/warfighter/geometry_nd.py`, `research_lab/warfighter/examples/geometry_10d_torus.json`, `research_lab/warfighter/tests/test_geometry_nd.py`.

**Interfaces:** `validate_geometry_problem(problem: Any) -> dict[str, Any]`; `project_to_3d(points: list[list[float]], matrix: list[list[float]]) -> dict[str, Any]`; `generate_geometry(problem: dict[str, Any]) -> dict[str, Any]`. Input declares `dimension` ∈ {6,10,11}, `point_count` 1..256, optional periodic radii list of positive finite floats, seed integer and explicit 3xN linear projection. Projected output contains at most 1000 vertices, `lossy_projection=true` for N>3, `mathematical_model_only=true`.

- [ ] **Step 1: Write failing tests**: 10D basis vectors projected by a declared 3×10 matrix have exact expected first three coordinates; invalid 3×9 matrix rejected; 6/10/11 accepted, 9/12 rejected; NaN, Inf, negative radii, >256 points, oversized generated mesh rejected. Assert 10D-to-3D is flagged non-invertible, even if projected points happen to occupy a 3D subspace.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_geometry_nd -v`. Expected RED.
- [ ] **Step 3: Implement** deterministic coordinate sampling for a toy product of periodic circles/coordinate axes, direct declared matrix multiplication, finite-value checks and all dimension/rank disclosure. No physical string theory inference.
- [ ] **Step 4: Run** focused test. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/geometry_nd.py research_lab/warfighter/examples/geometry_10d_torus.json research_lab/warfighter/tests/test_geometry_nd.py && git commit -m "feat(warfighter): bounded higher-dimensional mathematical projections"`.

### Task 3: Read-Only Research Lens Snapshot

**Files:** Create `research_lab/warfighter/lens_snapshot.py`, `research_lab/warfighter/tests/test_snapshot.py`.

**Interfaces:** `snapshot(*, mode: str, mathematical_output: dict, research_status: str, source_sha256: str) -> dict[str, Any]` and `validate_snapshot(payload: dict[str, Any]) -> dict[str, Any]`. Modes: hilbert-halo, statevector-constellation, compactification-loom. Status enum includes SYNTHETIC, VERIFIED_FOR_MODEL, HUMAN_REVIEWED_RESEARCH, STALE, MISSING; no OPERATIONAL flag. No write-capable journal or PINEAL store handle enters this module.

- [ ] **Step 1: Write failing tests**: valid mode/actual digest and truth labels retained; remove passwords, raw notes, user identities, host path, escape/control characters, precise geolocation, hidden prompts; require digest and source-kind, preserve model assumptions; unknown live state rejected instead of fabricated.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_snapshot -v`. Expected RED.
- [ ] **Step 3: Implement** strict whitelisted numeric/content fields, size cap 1 MiB and copy-only normalization. Output deterministic abstract shapes and status; never call research publication or PINEAL writes.
- [ ] **Step 4: Run** focused test. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/lens_snapshot.py research_lab/warfighter/tests/test_snapshot.py && git commit -m "feat(warfighter): sanitize mathematical visualization snapshots"`.

### Task 4: Live Terminal Constellation Renderer

**Files:** Create `research_lab/warfighter/lens_terminal.py`, `research_lab/warfighter/tests/test_lens_terminal.py`.

**Interfaces:** `render_frame(snapshot: dict[str, Any], *, frame: int = 0, width: int = 80, color: bool = False) -> str`; `watch(snapshot: dict[str, Any], *, frames: int | None = None, interval: float = 0.5, stream: TextIO | None = None) -> int`. Project 3D points to terminal rows/columns with rotation around view axis; D4 time animates pulse, D5 mathematical memory/evidence status and D6 compute mode are textual channels, not spatial dimensions.

- [ ] **Step 1: Write failing tests**: deterministic frame 0 for golden fixture, visibly different rotation at frame 1, bounded width 40..160, frame max 1000, interval 0.1..5, `NO SIGNAL` for missing state, non-TTY finite frames omit unrequested ANSI escapes and render readable six-channel legend; control-character injection cannot manipulate terminal.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_lens_terminal -v`. Expected RED.
- [ ] **Step 3: Implement** small orthographic rotating projected point cloud with depth-sort ASCII glyphs, labeled modes and explicit SYNTHETIC/RESEARCH_ONLY status. Clamp canvas and avoid unbounded sleep/work; Ctrl-C exits viewer only.
- [ ] **Step 4: Run** focused test. Expected GREEN; three-frame non-TTY output finite.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/lens_terminal.py research_lab/warfighter/tests/test_lens_terminal.py && git commit -m "feat(warfighter): rotating terminal mathematical cortex"`.

### Task 5: Optional Editable Blender Model and Static GLB Export

**Files:** Create `research_lab/warfighter/blender_lens.py`, `research_lab/warfighter/tests/test_blender_export.py`.

**Interfaces:** `generate_scene(snapshot_file: Path, output_dir: Path) -> dict[str, str]` is invoked **inside** local Blender's `bpy` runtime via `blender --background --python research_lab/warfighter/blender_lens.py -- --snapshot FILE --output DIRECTORY`. Outputs `gpt-doug-quantum-lens.blend`, `gpt-doug-quantum-lens.glb` and `lens-manifest.json`. Names are stable collections: FOUNDATION, HILBERT_HALO, STATEVECTOR_CONSTELLATION, COMPACTIFICATION_LOOM, PROVENANCE_SPINE, ZYRA_GOVERNANCE.

- [ ] **Step 1: Write failing tests**: validate generator entrypoint/manifest schema; default <=200 objects and <=50000 polygons, 1 MiB snapshot limit; sample scene names, static export label; no overwrites outside explicitly chosen output dir, no writes to `integrations/gpt-doug-pineal/cad/build`; absent Blender yields graceful OPTIONAL_DEPENDENCY_MISSING, never installs a package.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_blender_export -v`. Expected RED.
- [ ] **Step 3: Implement** bounded low-poly meshes/materials/emissive rings and named selectable objects in bpy; preserve editability in .blend and accurately call GLB a static **snapshot**. An optional `blender -b --python ...` smoke test opens .blend and validates mesh collection count if Blender is present.
- [ ] **Step 4: Run** focused test and Blender smoke if installed; expected GREEN or explicitly SKIPPED for optional Blender, not silently claimed run.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/blender_lens.py research_lab/warfighter/tests/test_blender_export.py && git commit -m "feat(warfighter): optional Blender quantum-lens scene export"`.

### Task 6: Read-Only CLI Integration, Documentation and End-to-End Tests

**Files:** Create `research_lab/warfighter/lens_cli.py` and `docs/WARFIGHTER_QUANTUM_LENS.md`, add `research_lab/warfighter/tests/test_lens_cli.py`; modify `research_lab/warfighter/cli.py` to delegate a `lens` subcommand. Existing shell wrapper stays under research-core guardrails.

**Interface:** `main(argv: list[str] | None = None) -> int`:
- `warfighter lens statevector FILE --input-root ROOT` -> JSON pure math output.
- `warfighter lens geometry FILE --input-root ROOT` -> JSON 3D projection + rank warning.
- `warfighter lens watch FILE --input-root ROOT --frames 3 --no-color` -> deterministic ASCII projection; `--watch` for operator live loop.
- `warfighter lens export FILE --input-root ROOT --output DIR --blender PATH` -> optional Blender background .blend/.glb.
- `warfighter lens doctor` -> dependency checks only; no installs.

- [ ] **Step 1: Write failing `test_lens_cli.py` asserting one-command statevector/geometry/3-frame watch outputs are stable, read-only, SYNTHETIC-labeled and do not invoke network, ontology publication, PINEAL writes, XQE dispatch or Blender when not exporting; absent optional Blender returns exit code 6 with actionable instructions.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_lens_cli -v`. Expected RED.
- [ ] **Step 3: Implement** CLI parsing and guarded explicit file root checks via research-core fixture helpers; never call shell through string concatenation; use fixed Blender process argument list and a user-provided installed executable path. Document all status labels, caveats, Mac/Apple Silicon start commands, example JSON and which files are editable/static.
- [ ] **Step 4: Run** `python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v` and `python3 -m unittest research_lab.tests.test_bio_hilbert research_lab.tests.test_multidimensional -v`. Check `bash scripts/doug-max warfighter lens doctor` only if guarded CLI integration and bash syntax pass; do not claim success from a design file. Expected GREEN for available components and documented optional SKIPs.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/lens_cli.py research_lab/warfighter/cli.py research_lab/warfighter/tests/test_lens_cli.py docs/WARFIGHTER_QUANTUM_LENS.md && git commit -m "feat(warfighter): read-only quantum lens terminal and export controls"`.

## Release Acceptance, Risks, and Creative Follow-On

- **Scientific truth:** diagrams render classical math and data semantics only. All UI must say what is MEASURED, SYNTHETIC, DERIVED, UNVERIFIED, or OFFLINE. No “extra dimensions unlocked” or real quantum hardware claims.
- **Data safety:** no real system integrations, no unreviewed finding publication, no implicit schema authority promotion. A Lens demo can be shared publicly without revealing private device data or PINEAL note bodies.
- **Visual acceptance:** show real output from the generated statevector and geometry snapshots, not a stock concept image; Blender GLB is an inspectable static mesh; .blend stores editable objects.
- **Nonfunctional:** low-poly, <=8 GiB machine friendly, bounded frames and memory, no surprise downloads. Explicitly document when optional Blender test was skipped.
- **Integration:** independent review of ANSI escaping, subprocess argument handling, purity and input bounds before PR; reference source SHA, model version, and schema status in sample screenshots.
- **Later path:** connect to the separately reviewed PINEAL 6D Biochip design through a **read-only** adapter once that project is actually implemented. Do not presume it exists because a conceptual drawing or spec exists.

This plan implements optional M3–M4 after the Warfighter Research Core. Review both written plans and choose an execution method before any product code changes.
