# GPT-Doug-PINEAL Biochip 6D: Terminal + Blender Design

**Date:** 2026-10-12
**Status:** Chat-level visual design approved; implementation awaits review of this written specification and a separate implementation plan.
**Repository:** sonoxo/gpt-doug-llm
**Target subsystem:** integrations/gpt-doug-pineal

## 1. Goal and success criteria

Give the operator a **working local representation** of the GPT-Doug software “biochip”: a rotating ANSI terminal projection and an editable, free-Blender 3D scene. Both should use telemetry from the existing local GPT-Doug heartbeat/memory state, show when signals are unavailable or stale, and run without paid LLM/API tokens.

Success means an operator can start a visual display from Terminal, inspect a named and editable 3D anatomy in Blender, export an interchangeable GLB, and verify that the display reflects deliberate changes to a local telemetry fixture. The visual anatomy is a software-system metaphor, **not** a physical biochip, biological device, six-spatial-dimensional object, validated circuit design, or connection to a human brain.

## 2. Existing implementation and boundaries

Verified in the repository main branch:

- \`integrations/gpt-doug-pineal/src/pineal/cli.py\` exposes the existing local-first \`pineal\` CLI, including \`blink\`, \`dashboard\`, and \`heartbeat\`.
- \`integrations/gpt-doug-pineal/src/pineal/blink.py\` provides terminal heartbeat visualization and established bounded watch/frames behavior.
- \`integrations/gpt-doug-pineal/cad/pineal_cad.py\` creates a separate **editable-source** CadQuery architectural assembly with STEP, DXF, STL and GLB exports. The new Blender component must **complement, not overwrite** these assets.
- The operator's Mac session has demonstrated \`~/Downloads/memory/working/heartbeat.json\` with ISO timestamp, load, RAM, disk, and nine memory-layer names; \`~/Downloads/memory/bio/anatomy.py\` is a standalone local anatomy viewer. These local files are *not* assumed to exist on CI runners or inside the GitHub checkout.
- The operator's machine showed Darwin/arm64 and about 8 GiB RAM. Default mesh and refresh budgets must be lightweight.

All inputs are read-only. The tool must neither terminate nor relaunch the running heartbeat, mutate PINEAL's ontology or SQLite database, nor write into existing CAD export directories without explicit \`--output\`.

## 3. The “6D” representation (precise meaning)

| Channel | Model meaning | Source | Presentation |
| --- | --- | --- | --- |
| D1 X | horizontal geometry | authored static mesh | 3D coordinate |
| D2 Y | depth geometry | authored static mesh | 3D coordinate |
| D3 Z | layered anatomy | authored static mesh | 3D coordinate |
| D4 Time | current timestamp, pulse phase, age/staleness | heartbeat timestamp | pulsing heart ring and frame phase |
| D5 Memory | measured memory-store counts/layer integrity | local anatomy/SQLite and directory checks | memory nodules, links, labels |
| D6 Compute | observed CPU load and available GPU/model *status*, when present | heartbeat load, optional local model status | color/brightness/rotation, numeric captions |

D4–D6 are **data attributes projected into a 3D visualization**; no fourth, fifth, or sixth physical spatial axis is claimed. CPU load is not CPU utilization. A GPU name or detected Ollama endpoint is not proof of GPU inference or GPU utilization. Unknown metrics must be labeled **UNMEASURED**, never inferred as active.

The terminal uses deterministic 3D-to-2D projection of a rotating core/rings/nodes, with time, memory, compute as independent animated/encoded channels and a compact six-channel text legend. Animations can be symbolic even when telemetry is missing, but the status must then say DEMO or NO SIGNAL.

## 4. Architecture and data flow

\`\`\`text
existing heartbeat loop (operator-managed) -----> working/heartbeat.json
optional anatomy.py (operator-managed) ----------> bio/anatomy.json
optional local memory count (read-only) ----------> bio/hippocampus.sqlite3
                                  |
                    safe local snapshot adapter
                    - file/size/type validation
                    - bounded read, timestamp parsing
                    - freshness and provenance tags
                    - normalized six-channel view
                                  |
                        +---------+-----------+
                        |                     |
               terminal projector       Blender scene adapter
               rotating ANSI frames     bpy mesh + materials
               2-5 Hz local draw        timer polls snapshots
                        |                     |
                    Terminal            editable .blend
                                             |
                                     snapshot .glb export
\`\`\`

Core snapshot JSON schema: \`schema_version\`, \`sampled_at\`, \`source_files\`, \`freshness\` (fresh/stale/missing/invalid), \`dimensions\` (x/y/z/t/memory/compute), \`hardware\` (CPU-load, RAM, disk, GPU name/status, model names when observed), \`layers\`, \`warnings\`. Each source retains a \`measured\` flag so visually compelling geometry cannot be mistaken for verified readings.

The **snapshot adapter** is separate from renderers, has no network access by default, validates all numeric data, bounds file sizes and node counts, and tolerates malformed/unavailable sources. Prefer the operator's existing \`memory\` directory; allow \`--memory-root\` / \`GPT_DOUG_MEMORY_ROOT\` override. Avoid collecting personal content from note text; counts and schema-level metadata suffice.

## 5. Terminal user experience

Integrate a nonbreaking \`pineal biochip\` group into the CLI:

- \`pineal biochip status --memory-root ~/Downloads/memory\`: print one JSON/summary snapshot and exit.
- \`pineal biochip watch --memory-root ~/Downloads/memory --interval 0.25\`: rotating ANSI projection, status, 6D legend, FPS cap, clear heartbeat-freshness indicator. Ctrl-C exits cleanly and leaves operator heartbeat running.
- \`pineal biochip export --memory-root ~/Downloads/memory --output ~/Downloads/memory/bio/exports\`: use installed local Blender in background to construct a project and a static GLB; no dependency download at runtime.
- \`pineal biochip launch --memory-root ~/Downloads/memory\`: when Blender exists, open a live Blender view plus terminal watch; otherwise run terminal watch with an explicit optional-Blender warning. Do not implicitly install software.

Support bounded \`--frames\` and \`--no-color\` for automated tests. A finite frame output on non-TTY must avoid escape/control sequences unless explicitly enabled.

## 6. Blender scene and export

The generator uses free Blender's bundled \`bpy\` API, launched by the CLI through a subprocess argument list (never a user-controlled shell string). A newly generated scene includes named, individually selectable/editable objects and collections:

1. FOUNDATION — substrate/baseplate, traces, labels.
2. GPU-LLM BRAIN — central faceted processor, up to four low-poly pods.
3. HEART — concentric heartbeat ring with emission material.
4. RAM / NERVOUS SYSTEM — fins and deterministic linking conduits.
5. MEMORY BIOCHIP — bounded nodules with provenance edges and semantic colors.
6. ZYRA SHIELD — clear perimeter/ring representing access governance.

For live GUI mode, a deliberately enabled \`bpy.app.timers\` callback reads local normalized state on a bounded 1–5 second cadence, updates materials/scales/labels on existing objects, and stops when the Blender session stops. A saved .blend should remain a useful editable *snapshot* without relying on auto-executed scripts; an exported .glb is a **snapshot**, not a promise of live streaming. Only a running Blender adapter is live.

Output names: \`gpt-doug-biochip-6d.blend\`, \`gpt-doug-biochip-6d.glb\`, \`biochip-6d-manifest.json\` with source timestamps, generated-at, status and explicit conceptual-model disclaimer.

Free Blender is an **optional local prerequisite**, not an installer dependency and not a paid service. Preserve existing CadQuery outputs under \`cad/build\` unchanged. A later importer may optionally pull the existing GLB as a base, but first release renders new geometry in Blender with stable semantic collection names.

Target Mac/8 GiB RAM: at most approximately 200 objects and 50,000 polygons for default scene; reuse meshes/materials, keep polling bounded, avoid large textures, heavy simulation and high-poly boolean operations. Display GPU hardware detection separately from activity telemetry.

## 7. Planned change surface

| Path | Responsibility |
| --- | --- |
| \`src/pineal/biochip6d.py\` | state normalization, freshness, terminal projection/watch and Blender launcher adapter |
| \`src/pineal/cli.py\` | add \`biochip\` commands without changing existing parser behavior |
| \`cad/blender_biochip.py\` | standalone Blender \`bpy\` scene assembly, live updating, .blend/.glb export |
| \`tests/test_biochip6d.py\` | fixture-driven state, projection, CLI and safety tests (no Blender required) |
| \`cad/verify_blender_biochip.py\` | optional Blender-installed geometry/export smoke checks |
| \`docs/BIOCHIP_6D.md\` | installation, commands, Apple Silicon guidance, truthful limitations |

Do not add a mandatory \`bpy\` or CadQuery requirement to the Python package; Blender supplies \`bpy\` in its own runtime. All new functionality is opt-in.

## 8. Error handling and privacy

- Missing, corrupt, old, or oversized heartbeat: show NO SIGNAL / STALE, never ONLINE from cached metadata alone; terminal keeps displaying informative fallback frames.
- Missing Blender: terminal features work, export returns a clear actionable error with free Blender installation instructions; do not auto-install.
- SQLite unavailable/locked: no persistent-memory content read; memory count UNKNOWN; do not mutate database.
- Blender GUI cannot start: report subprocess failure, leave the terminal/watch and existing heartbeat intact.
- Prevent accidental local disclosure: sample filenames and numeric metrics only, no note bodies, credentials or tokens in renders/manifests.
- No network access, remote data collection, service injection, filesystem-wide crawling, privilege escalation, autonomous persistence, or self-modifying model functionality.

## 9. Verification/acceptance criteria

1. Fixture-driven test for numeric and ISO8601 heartbeat timestamps, absent keys and malformed JSON.
2. Freshness classification correct near boundaries, with invalid/future timestamps visibly distinguished.
3. Terminal outputs exactly six labeled channels, clean bounded frames, and no required third-party Python packages.
4. Memory-store content never altered by status/watch/export: compare file modification times and/or hashes on fixture sources.
5. Simulated heartbeat metrics changed between frames update numeric text and the terminal projection signal.
6. Blender smoke test (if Blender installed): at least six semantic collections/assemblies; editable named objects; \`.blend\` reopens; \`.glb\` exports with valid mesh nodes; no existing CAD artifacts modified.
7. Live Blender scene updates from a subsequent snapshot; exported GLB remains explicitly static.
8. Existing PINEAL CLI and \`blink\`/CAD tests still pass.
9. CPU/RAM usage stays appropriate for an 8 GiB Apple Silicon Mac, with predictable process shutdown via Ctrl-C.
10. All display states differentiate LIVE telemetry, STALE, MISSING and synthetic DEMO.

## 10. Release sequence

Implementation plan should order work as (1) fixtures and snapshot adapter tests, (2) terminal six-channel visualization and CLI, (3) optional Blender generator/export/GUI adapter, (4) Blender smoke tests and docs, (5) end-to-end Mac instructions. Perform tests before claims of completion.

**Design review request:** approve this spec or request corrections. Only after approval, draft and review a detailed implementation plan, then implement on an isolated branch. No application code is changed by this design commit.
