# MECHA Visual Cortex and Standalone Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the verified offline MECHA research core with high-dimensional toy geometry, optional editable Blender exports, an offline browser viewer and a reproducible release of the same portable package to `sonoxo/mecha`.

**Architecture:** The canonical source remains `sonoxo/gpt-doug-llm/mecha/`. All visual outputs are sanitizations of research-only synthetic snapshots, never live defense or robotic telemetry. A reviewed, commit-pinned distribution process exports only the standalone subtree after running identical tests in both repositories.

**Tech Stack:** Python 3.9+ standard library, existing portable `mecha` modules; optional free Blender 4.x `bpy`; static ES modules/HTML for browser display (no CDN or mandatory npm); Git SHA-256/source-tree validation and GitHub CI. No hosted service, paid model API, biological hardware, physical actuator, or quantum processor.

**Spec:** `docs/superpowers/specs/2026-10-12-mecha-dual-repo-biopineal-design.md`. **Prerequisite:** the core plan `docs/superpowers/plans/2026-10-12-mecha-warfighter-offline-activation.md` has been implemented, reviewed and green in its development branch. This plan is the separately reviewable M2–M4/M5 optional component set.

## Global Constraints

- MECHA remains `SYNTHETIC` and `RESEARCH_ONLY`; any true operations, real hardware, weapon control, classified data, biometric collection and defense-system commands remain unavailable.
- “6D cortex” means three displayed/projected spatial coordinates plus time, provenance/memory and compute-label channels; 10D/11D geometry is **mathematical only** and 3D projection is lossy.
- Geometry accepts only 6/10/11 ambient dimensions, <=256 source samples, <=1000 output vertices and finite 3xN declared projection matrices; never claim observed physical extra dimensions.
- Blender is an optional installed local executable: no pip/npm/Blender autoinstall. Editable `.blend` and static `.glb` are labeled correctly and only generated on explicit export request. Size limits: <=200 objects, <=50000 polygons.
- Public MECHA artifacts must omit Agent10 callsign, military-affiliation claims, private memory, absolute host paths, tokens, credentials, customer data, nonpublic PINEAL notes and third-party patent claim implementations.
- Standalone `sonoxo/mecha` receives the **portable source subtree only**. It must not import the GPT-Doug monorepo, host adapters, source rights outside the first-party license, or preexisting proprietary third-party hardware integrations.
- Versioned GitHub release is commit-pinned, reproducible and one-way; no force push, unauthorized default-branch merge, branch-protection change, automatic overwrite or bypass of independent code review.
- Renderer, physics toy, browser viewer, and sync script are all **non-operational**; none write to research review journal, PINEAL database, ZYRA policy, or external robotics endpoint.
- Work in dependency order with RED/GREEN/commit per task. Do not create a new external GitHub repository before the implementation plans are approved and portable package can pass tests.

## Review Focus

1. **3x11 projection silently drops coordinate values:** labels must declare dimension, rank loss and assumed mathematical model rather than pretend invertibility (Task 1).
2. **Malicious snapshot label injects browser/terminal escape or HTML:** only whitelisted numeric/enum data should pass; no arbitrary innerHTML or unescaped filenames in exports (Tasks 2–4).
3. **Blender not installed:** JSON/terminal and standalone tests still work; export command reports OPTIONAL_DEPENDENCY_UNAVAILABLE, not a fake success or failed auto-install (Task 3).
4. **Local operator alias or private path leaks into public GLB or release manifest:** reject or redact on import, scan bytes and cross-test exported names/custom properties (Tasks 2–3, 5).
5. **The standalone mirror drifts or receives monorepo-only code:** source-tree hash and fixture-output comparison must fail release if a single tracked package file or generated quantum result differs (Tasks 5–7).

---

## File Map

| Path | Purpose |
| --- | --- |
| `mecha/mecha/geometry_nd.py` | Bounded 6/10/11D toy geometry and declared 3D projection |
| `mecha/tests/test_geometry_nd.py` | Dimension, finite values, rank-loss and cap tests |
| `mecha/mecha/visual_manifest.py` | Strict sanitized export schema + digest |
| `mecha/tests/test_visual_manifest.py` | Provenance, identity privacy, no command/secret data |
| `mecha/mecha/render/blender_scene.py` | Optional bpy generator, editable collections and GLB static export |
| `mecha/tests/test_blender_scene.py` | Optional Blender smoke, object/poly bounds and safe output |
| `mecha/web/index.html`, `mecha/web/viewer.js`, `mecha/web/viewer.css` | Local static snapshot explorer |
| `mecha/tests/test_web_viewer.py` | HTML/JS import boundaries and safe rendering checks |
| `mecha/mecha/cli.py` | Add `geometry`, `blender-export` and `export-manifest` commands |
| `mecha/tests/test_lens_cli.py` | Optional lens terminal/export CLI integration |
| `mecha/scripts/release-check.py` | Portable subtree release validator and file/digest manifest |
| `mecha/tests/test_release_check.py` | Reject package drift, illicit host-only content and mismatched outputs |
| `mecha/NOTICE.md`, `mecha/SECURITY.md` | Honest source/rights/safety disclaimers |
| `docs/MECHA_VISUAL_CORTEX.md` | Local visual examples, prerequisites and observed smoke-test results |
| `docs/MECHA_STANDALONE_RELEASE.md` | Reviewed twin-repo distribution and rollback |
| `.github/workflows/mecha-research.yml` | Extend existing portable/host tests for geometry/exports |
| `.github/workflows/mecha-release-check.yml` | Release comparison gate; no uncontrolled publish/write |
| `sonoxo/mecha` (separate repo after approval) | Same portable subtree and versioned release manifest |

### Task 1: Honest 6D/10D/11D Mathematical Projection

**Files:** Create `mecha/mecha/geometry_nd.py` and `mecha/tests/test_geometry_nd.py`.

**Interfaces:** `project_to_3d(points: list[list[float]], matrix: list[list[float]], *, dimension: int) -> dict[str, Any]`; `generate_toy_geometry(*, dimension: int, point_count: int, seed: int, matrix: list[list[float]]) -> dict[str, Any]`. Allowed dimension `{6,10,11}`, point_count 1–256, at most 1000 emitted vertices. Projection matrix exactly 3xN with finite floats, coords finite and within fixed +/-1000000 toy units, 32-bit nonnegative seed. Return `ambient_dimension`, `projected_dimension=3`, `lossy_projection=true`, `physical_dimensions_observed=false`, and `model="TOY_COORDINATE_PROJECTION"`.

- [ ] **Step 1: Write failing `test_geometry_nd.py`**: a 3x10 matrix selecting first three coordinates yields expected xyz for input e1/e2/e3, a 3x11 correctly maps known test vector, malformed 3x9/4x10 rejected, 9D rejected, 257 points rejected, NaN/Inf rejected; all 6/10/11D results disclose rank loss.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_geometry_nd.py' -v`. Expected RED.
- [ ] **Step 3: Implement** pure seeded coordinate generator and explicit matrix multiplication with finite checks; no physics prediction, hidden dimensional lift or GPU reliance.
- [ ] **Step 4: Run** focused test. Expected GREEN; output deterministic on repeat.
- [ ] **Step 5: Commit** `git add mecha/mecha/geometry_nd.py mecha/tests/test_geometry_nd.py && git commit -m "feat(mecha): finite high-dimensional toy projection"`.

### Task 2: Immutable Public Export Manifest and Privacy Guard

**Files:** Create `mecha/mecha/visual_manifest.py` and `mecha/tests/test_visual_manifest.py`.

**Interfaces:** `build_visual_manifest(snapshot: Mapping[str,Any], *, upstream_sha: str, model_version: str) -> dict[str,Any]`; `validate_visual_manifest(payload: Mapping[str,Any]) -> dict[str,Any]`. Require actual 40-character Git SHA-1 or 64-character SHA-256 upstream source commit string as recorded by the repo; source fixture digest 64 lowercase hex, visible model/lossy flags and `REAL_WORLD_ACTUATION=false`. Exclude all operator identity, user paths, tokens, private PINEAL note text and patent claim materials. Generated labels fixed enums, not user-supplied shader script or arbitrary JS.

- [ ] **Step 1: Write failing `test_visual_manifest.py`**: valid frozen snapshot and explicit upstream commit produce stable digest except timestamp metadata; changed fixture digest changes release hash; malicious values `Agent10`, `token`, `SECRET`, full home directory path, HTML/script payload, TTY escape, `operational_authority=true` reject; no public operator object even when host-private snapshot has one.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_visual_manifest.py' -v`. Expected RED.
- [ ] **Step 3: Implement** strict exported schema with all fields picked, canonical JSON using Task 1 core helpers, 1 MiB limit; strip or deny untrusted/private fields rather than copying input wholesale.
- [ ] **Step 4: Run** focused test. Expected GREEN.
- [ ] **Step 5: Commit** `git add mecha/mecha/visual_manifest.py mecha/tests/test_visual_manifest.py && git commit -m "feat(mecha): public-safe visual provenance manifest"`.

### Task 3: Optional Editable Blender MECHA Scene

**Files:** Create `mecha/mecha/render/blender_scene.py` and `mecha/tests/test_blender_scene.py`.

**Interfaces:** `generate_scene(snapshot_file: Path, output_dir: Path) -> dict[str,str]` only when launched in an explicitly supplied Blender 4.x `bpy` process. CLI supplies installed executable by validated path; command shape `blender --background --python mecha/mecha/render/blender_scene.py -- --snapshot INPUT --output DIR`. Outputs `mecha-biochip.blend`, `mecha-biochip.glb` (static), `manifest.json`. Collections `FOUNDATION`, `BRAIN`, `BIOPINEAL_HEART`, `MITOCHONDRIA`, `SYNTHETIC_ROBOTICS`, `PROVENANCE`, `ZYRA_SHIELD`.

- [ ] **Step 1: Write failing `test_blender_scene.py`**: validated snapshot yields fixed manifest and collection names; <=200 objects, <=50000 faces, labels SYNTHETIC/RESEARCH_ONLY, GLB is static; deny arbitrary input path symlinks, output directory escape, secret custom property, Python scripts embedded in fields or unapproved path overwrite. Missing Blender yields explicit OPTIONAL_DEPENDENCY_UNAVAILABLE in CLI, no installs.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_blender_scene.py' -v`. Expected RED for absent generator; Blender integration case may SKIP if not installed.
- [ ] **Step 3: Implement** deterministic low-poly meshes/materials and safe explicit output directory confinement. Use installed `bpy` when available; headless fallback never writes a fake .blend/.glb. No asset download, no command execution from snapshot.
- [ ] **Step 4: Run** focused Python tests and, **if Blender installed**, `blender --background --python mecha/mecha/render/blender_scene.py -- --snapshot <valid-synthetic-snapshot> --output <temporary-test-dir>`; expected GREEN on required tests, optional integration marked SKIPPED otherwise.
- [ ] **Step 5: Commit** `git add mecha/mecha/render/blender_scene.py mecha/tests/test_blender_scene.py && git commit -m "feat(mecha): optional editable Blender cortex and static GLB"`.

### Task 4: Local Browser Viewer (No Network Runtime)

**Files:** Create `mecha/web/index.html`, `mecha/web/viewer.js`, `mecha/web/viewer.css`, `mecha/tests/test_web_viewer.py`.

**Interfaces:** static HTML loads a local `manifest.json` via user-chosen local file picker (no fetch or CDN) or a bundled synthetic inline sample; renders only sanitized state with DOM `textContent` and a Canvas 2D wireframe. The page has source/limits/caveat labels, keyboard-pausable animation and clear error for malformed JSON. No telemetry, geolocation or external scripts.

- [ ] **Step 1: Write failing `test_web_viewer.py`**: no network/CDN imports, no remote fetch, no `innerHTML` unsafe interpolation, no remote images or analytics; keyboard tab labels and pause controls present; no arbitrary evaluation or data export; synthetic source label and file picker explicit.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_web_viewer.py' -v`. Expected RED for missing files.
- [ ] **Step 3: Implement** plain static canvas viewport and safe text-only labels. Browser file content is untrusted; validate size and schema before use, do not deserialize into code or persist sensitive data.
- [ ] **Step 4: Run** focused checks and optional browser smoke if a headless browser exists; expected GREEN on tests, optional browser test SKIPPED with explanation if unavailable.
- [ ] **Step 5: Commit** `git add mecha/web mecha/tests/test_web_viewer.py && git commit -m "feat(mecha): offline static research cortex viewer"`.

### Task 5: Portable Release Validation and Licensing

**Files:** Create `mecha/scripts/release-check.py`, `mecha/tests/test_release_check.py`, `mecha/NOTICE.md`, `mecha/SECURITY.md`, `docs/MECHA_STANDALONE_RELEASE.md`.

**Interfaces:** `validate_portable_release(package_root: Path, *, expected_upstream_sha: str) -> dict[str,Any]` and CLI `python3 mecha/scripts/release-check.py --package-root mecha --upstream-sha SHA --output MANIFEST`. Read-only validation by default, only writes to explicitly allowed output path; manifest contains individual relative paths and SHA-256 digests plus pinned upstream commit identifier.

- [ ] **Step 1: Write failing `test_release_check.py`**: canonical subtree passes; extra `integrations/mecha_bridge` file, `.env`, `operator-profile.json`, absolute host path, private PINEAL DB, `__pycache__`, copied third-party patent material, or altered tracked file fails; rejected symlink escape; comparison of golden Bell and rover JSON outputs is identical from portable root without host imports.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_release_check.py' -v`. Expected RED.
- [ ] **Step 3: Implement** deterministic whitelist release manifest (Python source, licensed docs, safe synthetic fixtures, tests, static viewer, optional Blender generator) and exact digest comparison. Cite parent GPL/MIT/third-party licenses correctly: don't assume a parent license conveys patent rights.
- [ ] **Step 4: Run** focused test and documented local `release-check.py` sample on synthetic package. Expected GREEN; no remote GitHub writes.
- [ ] **Step 5: Commit** `git add mecha/scripts/release-check.py mecha/tests/test_release_check.py mecha/NOTICE.md mecha/SECURITY.md docs/MECHA_STANDALONE_RELEASE.md && git commit -m "build(mecha): reproducible portable release and rights validation"`.

### Task 6: Lens CLI / Headless Integration

**Files:** Modify `mecha/mecha/cli.py`, create `mecha/tests/test_lens_cli.py` and `docs/MECHA_VISUAL_CORTEX.md`; extend `.github/workflows/mecha-research.yml`.

**Interfaces:** add `geometry FILE --input-root ROOT`, `blender-export SNAPSHOT --input-root ROOT --output DIR --blender PATH`, `export-manifest SNAPSHOT --input-root ROOT --output DIR` to existing portable CLI. Geometry and manifest are synchronous and bounded; Blender subprocess is explicit and never invoked for `doctor`, `demo`, `watch`.

- [ ] **Step 1: Write failing `test_lens_cli.py`**: 10D toy fixture produces lossy 3D projection JSON; invalid dimension rejects with nonzero code; standalone doctor and Bell scenario still work without Blender; export is SKIPPED/unavailable without executable; recognized installed Blender path uses fixed subprocess argument list, no shell interpolation; output manifest omits private labels; ordinary CLI does not instantiate PINEAL, ZYRA or sockets.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_lens_cli.py' -v`. Expected RED for absent commands.
- [ ] **Step 3: Implement** minimal adapter from tasks 1–5 and truthful text. Update docs with *observed* output and explicit speculative vs physical/hardware distinctions.
- [ ] **Step 4: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_*.py' -v`; add optional Blender smoke when available. Expected GREEN on required tests, optional marked SKIPPED if unavailable. Maintain existing GPT-Doug research regression green.
- [ ] **Step 5: Commit** `git add mecha/mecha/cli.py mecha/tests/test_lens_cli.py docs/MECHA_VISUAL_CORTEX.md .github/workflows/mecha-research.yml && git commit -m "feat(mecha): guarded optional visual export commands"`.

### Task 7: Create Reviewed Standalone MECHA Repository and Enforce Mirror Equivalence

**Files:** Add `.github/workflows/mecha-release-check.yml` in upstream; create standalone `sonoxo/mecha` repository (only after **plan approval and completed preceding acceptance gates**), containing the portable subtree + manifest, README/license/SECURITY/NOTICE as appropriate, CI with Python 3.9 and 3.13.

**Interfaces:** explicit operator-authorized repo creation (public, owner `sonoxo`); reviewed one-way distribution from a **specific reviewed upstream commit** using `git subtree split --prefix=mecha <sha>` or equivalently reproducible filtered copy; provenance manifest records upstream source path/tree SHA, published repo commit SHA and source checksums. Do not silently copy entire monorepo or force merge into standalone default branch.

- [ ] **Step 1: Write failing release equivalence tests** on fixture output and source checksums. On a purposely modified mirrored `quantum.py`, release gate must fail even when local tests pass. A stale or missing standalone repo must return `MIRROR_NOT_PUBLISHED`, not claim success. Ensure no host adapters, `.env`, callsign, credentials or other local memory leaks into standalone tree.
- [ ] **Step 2: Run** `PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_release_check.py' -v` and local mirror comparison test; expected RED before mirror publication/helper logic is added.
- [ ] **Step 3: Add** a read-only GitHub Actions verify/compare job and an explicit-reviewed export procedure. Then create `sonoxo/mecha` using connected GitHub account **only after** user approves execution and the repository-name availability/permissions are verified, populating it with exactly the reviewed subtree. No force push, branch protection alteration, hidden deploy token or unreviewed default-branch merge.
- [ ] **Step 4: Run** same golden tests on source checkout and standalone checkout, compare fixture JSON digests and distributed file hashes, verify both CI matrices pass, confirm README does not imply real robotics/quantum/wetware government certification. Expected GREEN and published artifact reference with exact checksums.
- [ ] **Step 5: Commit/review** the upstream release-check workflow and publish a reviewed mirror commit/PR with provenance manifest; retain known upstream SHA in both repo descriptions/release docs. If any check fails, label OUT_OF_SYNC and keep source unchanged.

## Final Acceptance and Rollback

- Test matrix: portable core, host adapter, exact BioPINEAL/Warfighter math, six-channel terminal, 6/10/11D geometry, Blender optional, static viewer, source manifest, rights and privacy, standalone cross-repo equivalence.
- End-user commands after verification: `bash scripts/doug-max mecha doctor`, `bash scripts/doug-max mecha demo --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples`, `PYTHONPATH=mecha python3 -m mecha.cli geometry ...`, and optional `blender-export`.
- User-visible truth labels are non-negotiable. No connected robot, actual military system, human neurons, physics demonstration of extra dimensions, autonomous command pipeline, quantum hardware, official safety approval, DoD ATO or patent license is created by visualization.
- Rollback removes optional renderer/host bridge route, restores previous reviewed portable release tag and disables mirror publication; existing `scripts/doug-max` guardrails, PINEAL data, ZYRA governance and remote robotics contracts remain unchanged.
- External repo `sonoxo/mecha` creation is a **later implementation milestone**, not an action authorized or performed by this planning document.
- Do not execute this plan until its human review is complete and the offline activation core plan's implementation and tests are verified.
