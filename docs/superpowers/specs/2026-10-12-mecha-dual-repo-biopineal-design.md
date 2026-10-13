# GPT-Doug MECHA — Dual-Repository Integration Architecture

**Design version:** 1.0.0  
**Date:** 2026-10-12  
**State:** PROPOSED — WRITTEN DESIGN FOR REVIEW; NOT YET IMPLEMENTED OR MERGED  
**Intended homes:** `sonoxo/gpt-doug-llm/mecha/` and a separately created public `sonoxo/mecha` repository  
**Concept name:** **MECHA — Modular Engineering Cortex & Hybrid Anatomy**  
**Operator persona:** Agent10 (private, self-declared alias; not an authenticated military identity)  
**Scope:** All requested components: BioPINEAL, Agent10, bounded classical quantum mathematics, mitochondrial compute-cost metaphor, offline robotics research, provenance, ZYRA/PINEAL read-only interoperability, 3D/6D and optional 10D/11D projection, testing, and separate repository distribution.

> **Truth boundary:** MECHA is a software research/simulation platform for authorized civilian/industrial robotics and synthetic defensive-readiness education. It is not a physical mecha suit, biochip, living neural interface, quantum computer, actual extra-dimensional device, official military system, weapons controller, safety-certified robot, or government authorization. A public GitHub project and MIT license cannot grant third-party patent or hardware rights.

## 1. User decision and measurable outcome

The user asked to “merge to mecha” and, when offered a choice between building MECHA in GPT-Doug and placing it in a separate MECHA repository, answered **“all.”** Interpret this as **both destinations and all previously specified software research integrations**, not authority to invent or bypass access to third-party systems.

The first acceptance milestone is **one offline MECHA demo** that, with synthetic fixtures, can render a read-only status frame, expose six correctly labeled simulation/data channels, project a bounded classical two-qubit Bell state with reproducible probabilities, show a toy industrial inspection rover, and publish an inspectable result manifest. It must run on macOS Apple Silicon and CI Linux without external network, privileged accounts, Blender, quantum hardware or paid tokens. A second optional command exports an editable Blender scene and a static GLB if Blender is installed.

The user will be able to operate this through **both** the GPT-Doug terminal command and a stand-alone MECHA checkout. A single canonical implementation prevents diverging math/governance semantics.

## 2. Verified repository foundation and dependency state

Read-only repository inspection established the following:

| Existing source | Current supported fact | MECHA integration boundary |
| --- | --- | --- |
| `research_lab/warfighter/biopineal.py` on BioPINEAL feature branch | Local heartbeat freshness and classical statevector computation; <=6 simulated qubits, <=128 gates, <=1024 shots, abstract compute budget | Use a read-only, optional provider adapter. Do not duplicate math into separate incompatible implementations or call it “quantum hardware.” |
| `research_lab/warfighter/operator_profile.py` on feature branch | Private, self-declared Agent10 callsign | Return only alias and SELF_DECLARED status, never forge a military role, clearance or permission. No profile is exported to public artifacts. |
| `research_lab/warfighter/biopineal_sources.py` on later feature branch | Hash-pinned research-source index; polymer patent and Cortical Labs CL1 are different origins | Only attribution/provenance cards, not patent license, copied engineering recipes or proof of hardware access. |
| `research_lab/warfighter/research_freedom.py` on later feature branch | Fixed descriptive NO_EXTRA_REVIEW_REQUIRED outcome for allowlisted offline research | This is not an authorization primitive. Never alter the actual guardrail preflight or publication approval. |
| `safety-shield/ontology/zyra-mss-v1.json` | Existing mission-support objects, source/evidence, permissions and human decisions | Read-only schema references; no operational readiness writes. |
| `integrations/gpt-doug-pineal/src/pineal/store.py` | Local SQLite memory/audit infrastructure | Optional *explicit* reviewed research-memory projection only; no automatic data collection or remote sync. |
| `integrations/gpt-doug-pineal/cad/pineal_cad.py` | CAD geometry exporter including GLB/STEP conventions | Reference or optional later geometry import; do not replace existing CAD output or assume Blender is installed. |
| `robotics-intel-site/rover-connector-contract.json` | Template: telemetry_read/health_read true; command_write=false; requires approval and audit for any future command proposal | MECHA v1 exposes simulated rover state and public-read reference only; no command-write implementation. |
| `robotics-intel-site/rover-registry.json` | Public NASA rover references; owned/authorized connector marked NOT_CONFIGURED | Do not manufacture live rover access, telemetry or credentials. |
| `robotics-intel-site/maven-drone-system.json` | Synthetic/authorized observation model, real_autopilot_link=false, targeting=false, autonomous external actions=false | No automatic vehicle/drone integration, person tracking, targeting, weapon cueing or real GPS route upload. |
| `scripts/gpt_doug_max_robotics_lab.py` | Civilian/industrial robot engineering package with legal/compliance preflight; ENGINEERING_DRAFT_ONLY | Generate derived concept-level schematics *only under existing checks*, never a certified/safe-to-build physical design. |
| `scripts/doug-max` | Existing guardrail preflight plus routed commands | Add a guarded `mecha` route **after** accepted tests, never an unconditional bypass. |

**Active staging status at design time:** Warfighter Core PR #344, Agent10/BioPINEAL PR #345, patent evidence PR #346, and research-freedom PR #347 are still OPEN DRAFT stacked PRs; their feature code is not assumed to exist on `main`. The new MECHA code is **not authorized to silently merge these four PRs**. Subsequent implementation must resolve dependencies in order and assess repo-wide regressions and independent code reviews.

GitHub discovery found **no accessible `sonoxo/mecha` repository** and no MECHA-named branch or directory in `sonoxo/gpt-doug-llm`. Create the external repository **only at the separately approved implementation phase**, not as an unnoticed side effect of documentation.

## 3. Architecture alternatives and selection

| Approach | Benefit | Cost/risk | Decision |
| --- | --- | --- | --- |
| A. MECHA module only in GPT-Doug | Fastest, fewest release components | Not a standalone MECHA product | Does not satisfy “all” |
| B. Two copied implementations | Two fully independent repos | Logic, safety rules and source attribution drift | Reject |
| **C. Single versioned engine, two repositories** | One math/ontology source of truth, both user-facing checkouts | Needs release/sync verification and two CI surfaces | **Recommended** |

**Selected design:** canonical, standard-library-first Python package source rooted at `gpt-doug-llm/mecha/`, with optional **host-only** adapters rooted at `gpt-doug-llm/integrations/mecha_bridge/`. The standalone `sonoxo/mecha` repository receives a commit-pinned, reviewed release of the package subtree. Every published version includes an upstream Git SHA and content manifest. It does not clone the whole GPT-Doug monorepo or silently bypass checks.

**One-way source rule:** code edits originate in the canonical MECHA package and are reviewed in GPT-Doug first. The external repository is distributed as a versioned product; fixes made externally must be proposed back upstream before a new distribution is published. A stand-alone user can run demos without GPT-Doug internals because the core package cannot import `research_lab`, `agents`, `pineal` or `scripts` at import time.

## 4. Conceptual runtime architecture

~~~text
                        GPT-DOUG-LLM (canonical source repository)
                                     |
         +---------------------------+-----------------------------+
         |                           |                             |
      BIOPINEAL                  ZYRA/PINEAL              ROBOTICS / CAD
      self-declared Agent10      read-only schemas        rover/drone contracts
      heartbeat state            reviewed research        civilian design gate
      classical math             optional projection      synthetic fixtures
         |                           |                             |
         +------------- EXPLICIT READ-ONLY HOST ADAPTERS ----------+
                                     |
                               MechaSnapshot v1
                           input contract + provenance
                                     |
       +-----------------------------+----------------------------+
       |                             |                            |
   MECHA CORE                   TERMINAL CORTEX              BLENDER EXPORT
   validated toy geometry       rotating projected points    optional editable .blend
   synthetic rover model        6 data channels              static .glb
   pure finite math             truthful LIVE/STALE flags    no hardware actuation
       |                             |                            |
       +------------------- local result manifest ----------------+
                                     |
                         versioned package release
                                     |
                           sonoxo/mecha (standalone)
                            same MECHA core package
                             synthetic offline CLI
                             no implied GPT-Doug access
~~~

Data flows exclusively from read-only adapters/fixtures into immutable model snapshots and renderers. No return path from a renderer to ZYRA authorization, PINEAL approval, robotic actuators, XQE task dispatch or government systems.

## 5. Core package boundaries

### 5.1 MECHA core — `mecha/core/`

**Purpose:** standalone reproducible research model. Expose strict typed declarative JSON schemas, allowed simulated robotics entities (IndustrialInspectionRover, SyntheticEnvironment, SensorHealth, PowerBudget, SimulatedJointPose, SafetyEnvelope), bounded CPU-only matrix/projection arithmetic, and deterministic toy scenario steps.

Inputs: <=64 KiB synthetic JSON, provenance plus a fixed version. Outputs: <=1 MiB `MechaSnapshot`, <=200 low-poly scene nodes for default sample, and run digest. No fetching, network, secrets, code execution from model data, third-party control or privileged direct reads.

**Mitochondria** means modeled operation-count budget, not biological ATP or an actual battery energy meter. **Quantum** means finite classical statevector mathematics, with explicit gate, shot, normalization and resource caps.

### 5.2 Host bridge — `integrations/mecha_bridge/`

**Purpose:** connect available GPT-Doug features to the portable MECHA data contract. All imports lazy/optional, with precise UNAVAILABLE statuses for missing draft or installed modules. Provide adapters:

- `BioPinealAdapter`: read the existing finite classical simulation result and heartbeat status, keeping fields `quantum_hardware_used=false` and `gpu_usage=UNMEASURED` when not observed.
- `OperatorAdapter`: inject only the local Agent10 alias and SELF_DECLARED provenance into a private *session snapshot*, not public release metadata.
- `EvidenceAdapter`: public patent/vendor index **read-only**, retain independent attribution and digest; never infer licensing or share proprietary text.
- `OntologyAdapter`: fetch/read approved `warfighter_research` and ZYRA schema references only, with no implicit project “operational authority” inference.
- `RoboticsAdapter`: read rover contract/registry and synthetic observation fixtures; real command_write remains false.
- `GovernanceAdapter`: display legal/security review state and approved resource ceilings; `research_freedom` does not return an execution token.

Adapters do not import/instantiate PINEAL persistent DB in a default read-only demo. A separate, reviewed future command may explicitly project public synthetic research into the existing namespace when publication workflow authorizes it; out of scope for v1.

### 5.3 Renderer interface — `mecha/render/`

Terminal: dependency-free ANSI/ASCII rotating 3D-projected wireframe, bounded FPS and `--frames`; visible source labels; gracefully disable color for non-TTY.

Blender: optional externally installed free Blender with bundled `bpy`; generate named collections FOUNDATION, BRAIN, BIOPINEAL_HEART, MITOCHONDRIA, SYNTHETIC_ROBOTICS, PROVENANCE, ZYRA_SHIELD. Save an editable `mecha-biochip.blend` and an explicitly static `mecha-biochip.glb`, plus a manifest with source digests. No Blender dependency for `doctor`, `demo` or `watch`. Never auto-download/execute third-party scripts.

Web viewer: optional later Three.js GLB reader, fully client-side/offline-capable and displaying the same explicit simulation labels. No required cloud deployment or telemetry collection.

## 6. Mathematical/6D model (precise meanings)

| Channel | Meaning | May be displayed as |
| --- | --- | --- |
| X | authored 3D horizontal geometry | coordinate |
| Y | authored 3D depth | coordinate |
| Z | authored 3D vertical geometry | coordinate |
| D4 time | frame index, local UTC timestamp, heartbeat age | pulse/animation |
| D5 memory | provenance status, count of explicitly permitted approved findings | links/nodules |
| D6 compute | CPU load sample where actually available; abstract quantum simulation operations separately | numerical legend/brightness |

Six channels do **not** mean six additional physical dimensions. The optional 10D/11D “string-inspired” mode uses bounded toy vectors and declared matrices projected into R^3. Projection is generally non-invertible and must label lost dimensional information. No result proves string theory or connects to a quantum processor.

The source of a rotation or synthetic pulse must be marked SIMULATED, not MEASURED. Stale heartbeat >20s is STALE even if its old JSON says ONLINE. A detected GPU name does not prove GPU workload; report GPU usage UNMEASURED unless directly instrumented.

## 7. Versioned contracts

### 7.1 Minimal MECHA snapshot

~~~json
{
  "schema_version": "1.0.0",
  "type": "MechaSnapshot",
  "system": "GPT-DOUG-MECHA",
  "source_kind": "SYNTHETIC",
  "authority": "RESEARCH_ONLY",
  "operator": {
    "callsign": "Agent10",
    "identity_state": "SELF_DECLARED",
    "government_credential_verified": false
  },
  "mode": "OFFLINE_ROBOTICS_DEMO",
  "channels": {
    "x": "AUTHORED_GEOMETRY",
    "y": "AUTHORED_GEOMETRY",
    "z": "AUTHORED_GEOMETRY",
    "time": "SIMULATED",
    "memory": "SOURCE_LABELS_ONLY",
    "compute": "CLASSICAL_TOY_MATH"
  },
  "hardware": {
    "connected_rover": false,
    "real_robot_commands_enabled": false,
    "quantum_hardware_used": false,
    "biological_hardware_connected": false
  },
  "source_sha256": "64-lowercase-hex-digest-of-actual-synthetic-fixture"
}
~~~

The example digest value is illustrative, not a valid persisted SHA-256; production schema must require an actual 64-digit lowercase hexadecimal digest, UTC timestamps, exact model version, committed code digest, safety state, data-rights label and deterministic inputs.

Public exports **must omit the operator object** by default. Only a private opt-in terminal session may show the local callsign; avoid leaking identity or privilege by metadata.

### 7.2 Public manifest minimum

`manifest.json` contains schema/version, upstream commit SHA, published MECHA source commit SHA, build timestamp, licensing notices, simulation/model versions, fixture digests, renderer mode, sample origin, limitations, and an explicit `REAL_WORLD_ACTUATION=false` field. It must not include host usernames, absolute private paths, tokens, military claims, copied vendor patent content, or hidden note text.

### 7.3 Future extension rules

New types and adapters are additive, versioned, tested, and disabled until explicit operator selection. Published data cannot create an arbitrary `executor` object, imported plugin code, hardware credential reference, or a new authorization level.

## 8. Operator commands (proposed; none implemented by this spec)

~~~text
# GPT-Doug wrapper
bash scripts/doug-max mecha doctor
bash scripts/doug-max mecha demo --fixture mecha/examples/synthetic-inspection-rover.json
bash scripts/doug-max mecha watch --frames 3 --no-color
bash scripts/doug-max mecha biochip --memory-root ~/Downloads/memory
bash scripts/doug-max mecha sources --topic biological_computing
bash scripts/doug-max mecha blender-export --output ~/Downloads/memory/mecha/exports

# Standalone checkout (after creation/release)
python3 -m mecha.cli doctor
python3 -m mecha.cli demo --fixture examples/synthetic-inspection-rover.json
python3 -m mecha.cli watch --frames 3 --no-color
python3 -m mecha.cli blender-export --output ./exports
~~~

Default to offline synthetic inputs. The `biochip` host command may read existing heartbeat state but must never start an unattended background daemon, write into PINEAL stores, generate robotic commands, or assume Agent10 has verified privileges. No command will silently provision credentials or access actual military systems.

## 9. Security, legal, and governance boundaries

- **Local-first, no surprise external actions.** New routines default to no networking, no scheduling, no filesystem-wide crawling, no unsolicited GitHub writes, no remote AI token usage, no cloud deployment, and no physical actuator interaction.
- **Human-controlled operations only.** Existing `scripts/doug-max` guardrail preflight, ZYRA policy, PINEAL synthetic metric allowlist and external authorization checks are preserved. The descriptive “research freedom” exception is never treated as a bypass token.
- **No weapons use.** Reject targeting, fire-control, weapon cueing, autonomous engagement, live force positions, hidden third-party robotics control, or field-action planning. Civilian/industrial inspection and synthetic training/defensive resilience exercises remain in scope.
- **Operator credentials.** Agent10 is an arbitrary callsign. It cannot be used as evidence of military employment, clearance, entitlement, government role, access to restricted systems, training certification or hardware ownership.
- **Third-party IP.** MIT covers properly licensed first-party software only. USPTO polymer records and the Cortical Labs CL1 page are separately attributed research references; no patent license, device access, vendor endorsement, copied claim-based manufacturing recipe or infringement clearance follows from citation.
- **Robotic safety.** Any real device integration or motion control demands a later design including ownership verification, authenticated API, hardware emergency-stop, safety risk analysis, regulatory standards, operator signoff and test environment; release v1 contains **no physical command-write endpoint**.
- **Public exports.** Show no private memory texts, credential names, host path, personal operator metadata, sensitive/protected data or classified/CUI datasets. Fail closed on unknown permissions and classifications.
- **Audit.** Hash/digest recording helps spot unintended file changes; an unsigned checksum is not identity authentication or legal certification. Future public releases use release notes and reproducible build provenance, with human code review.

## 10. Two-repository workflow and release gates

1. Develop proposed `mecha/` portable package on a dedicated GPT-Doug feature branch **after this spec and its implementation plan are approved**. Do not merge open draft dependency PRs #344–#347 as a shortcut.
2. Test canonical portable package on Python 3.9 and 3.13, macOS arm64 and Linux where runners are available. Run existing BioPINEAL, Warfighter, ZYRA/PINEAL and robotics-regression checks in the full repository. Required existing policy files remain byte-for-byte unchanged.
3. Independently review scope, command/write boundaries, data classification, dependencies, Blender subprocess handling, provenance, user-data leakage and license/third-party branding.
4. Following approval, create a distinct **public** repository `sonoxo/mecha` with matching attribution, MIT code license only where applicable, README scope limitation, security disclosure link, reproducible fixtures and CI.
5. Publish the portable package as an immutable upstream-subtree release (for example a reviewed `git subtree split --prefix=mecha` commit), tagged with the upstream GPT-Doug commit SHA and source-tree digest. **Do not auto-force-push** MECHA. If a mirror PR is necessary, require human review before its merge.
6. Keep optional monorepo host adapters under `integrations/mecha_bridge/` (not copied into standalone) to avoid unresolved imports and private data dependencies. The standalone distribution exercises the same math and rendering core, without pretending that GPT-Doug credentials, ZYRA data or PINEAL stores are available.
7. For updates or hotfixes, modify the upstream core, test both contexts, publish new version, compare generated artifacts, and refuse release if test or provenance hashes diverge. No silent syncing or overwriting a release tag.

There is **no default-branch merge** from a PR merely because the dual-repo design is approved. Each source PR needs green checks, independent review and normal repository merge permissions.

## 11. Proposed change surface

### GPT-Doug canonical repository (future implementation)

| Proposed path | Purpose |
| --- | --- |
| `mecha/README.md`, `mecha/pyproject.toml` | Portable package entry point, licensing, installation |
| `mecha/mecha/core.py`, `mecha/mecha/schema.py` | No-dependency strict synthetic world/state contract |
| `mecha/mecha/quantum.py`, `mecha/mecha/geometry_nd.py` | Pure bounded classical mathematics; share canonical algorithms through reviewed adapters or extracted common code, not unreviewed copies |
| `mecha/mecha/robotics.py`, `mecha/examples/synthetic-inspection-rover.json` | Synthetic environment and industrial/inspection robot fixtures |
| `mecha/mecha/render/terminal.py` | Six-channel rotating terminal projection |
| `mecha/mecha/render/blender_scene.py` | Optional installed-Blender scene generator |
| `mecha/mecha/cli.py` | Standalone offline CLI |
| `mecha/tests/test_*.py` | Contract/limits, privacy, math, projector, integration and CLI tests |
| `integrations/mecha_bridge/` | Optional host-only adapters for BioPINEAL, Agent10, PINEAL/ZYRA, robotics, provenance |
| `tests/test_mecha_bridge.py` | Existing service contract compatibility and permissions |
| `scripts/doug-max` | Guarded `mecha` dispatch, no privilege exception |
| `docs/MECHA.md` | User-facing architecture/status/run instructions |
| `.github/workflows/mecha-research.yml` | CI with both Python versions, license/policy and source checks |

### Standalone repo (after approval)

`sonoxo/mecha` will contain only the signed-off portable subtree and source-mapping manifest, reproducible releases, synthetic examples, accessible docs and tests. The standalone repository **must not claim** PINEAL/ZYRA live connections unless independently configured and authorized in a distinct follow-on release.

## 12. Verification matrix

1. **Standalone import:** Python can import `mecha` with no GPT-Doug, PINEAL, ZYRA or network runtime installed; no import-time filesystem mutation.
2. **Twin outputs:** identical synthetic fixture and package version generate identical JSON/quantum/geometry results in standalone and hosted CLI, discounting explicitly non-semantic timestamps.
3. **Quantum correctness:** Bell |00>→H(0),CNOT(0→1) returns probability 0.5/0.5; malformed gate, >6 qubits, >128 gates, >1024 shots, and abstract compute-budget overrun rejected.
4. **Simulation correctness:** finite, bounded rover pose and sensor data; model cannot return an authenticated motion command.
5. **6D truth:** verify three physical display coordinates plus three data channels; 10D/11D projection rank-loss warning; deterministic finite frames, no ANSI injection.
6. **Heartbeat truth:** STALE/MISSING/INVALID/FUTURE are explicit; never "LIVE" merely because stale JSON says "ONLINE".
7. **Identity privacy:** Agent10 SELF_DECLARED remains private and absent from public source/export; a forged government-role field is rejected.
8. **No policy bypass:** current guardrail preflight and project authorization untouched; malicious `research_freedom` payload cannot enable privileged actions.
9. **Source integrity:** USPTO application and Cortical Labs remain separate; no false patent ownership/integration or implied IP grant; pinned source/digest checks retain their meaning.
10. **Robotics boundaries:** no driver imports, real auto-pilot, person tracking, weapons, targeting, credential requests or actual rover/drone actuator calls, even when fixture contains tempting fields.
11. **Optional graphics:** missing Blender yields useful OPTIONAL_DEPENDENCY_UNAVAILABLE error; ordinary terminal/JSON tests still work. With Blender available, .blend is editable and .glb is valid, static and within low-poly budgets.
12. **Release reproducibility:** the public subtree is generated from a named canonical commit, tested against the same fixtures, tagged and checked for source drift. Existing ZYRA/PINEAL baseline contracts unchanged.
13. **Repo-level regressions:** run the focused MECHA suite, existing Warfighter/BioPINEAL source/Agent10 tests, PINEAL store/federation, ZYRA governance, and robotics-compliance tests; report unrelated existing red checks rather than concealing them.
14. **No inferred certification:** health labels, formal math verification, research review and public release never imply DoD authority, scientific proof, electrical safety certification or patent freedom-to-operate.

## 13. Errors, containment, rollback

- Missing BioPINEAL draft dependency or damaged local memory store: MECHA falls back to isolated synthetic demo with `ADAPTER_UNAVAILABLE` and no claim of connection.
- Missing MECHA standalone repository: do not invent remote URL or claim a merge. Host package can operate locally once implemented; standalone release requires explicit repo creation and confirmation.
- Unavailable/failed Blender process: avoid partial or mislabeled exports; report failure without affecting existing CAD assets.
- Schema mismatch, path traversal, forged permission field, non-synthetic Warfighter input, oversized payload, nonfinite numerical matrix: reject before simulation and preserve safe state.
- External repository synchronization failure: leave reviewed upstream version intact, mark mirror OUT_OF_SYNC, and do not force-push or claim release success.
- End-user Ctrl-C exits only the user-started renderer; leave the existing BioPINEAL heartbeat and unrelated processes untouched.
- Rollback disables wrapper/adapter and restores previous release tag, without editing canonical ZYRA governance or PINEAL SQLite content.

## 14. Dependency-sensitive execution milestones

**M0 — portable research core:** schema, synthetic rover/energy/quantum snapshot, manifest, tests, terminal status. Design *all* integrations but implement smallest coherent offline sample first.

**M1 — hosted BioPINEAL bridge:** Agent10 local alias, classical math, heartbeat, curated sources and truthful governance, after draft PR dependencies are reviewed. Existing policy files untouched.

**M2 — 3D/6D presentation:** rotating terminal, optional Blender editable .blend and GLB, static snapshot manifests. Separate optional 10D/11D geometry follows with exact disclosures.

**M3 — robotics/ontology integration:** read-only rover contract/public mission references, synthetic inspection environment and simulator; ZYRA/PINEAL metadata integration remains read-only/explicitly controlled.

**M4 — standalone repository:** create `sonoxo/mecha`, perform reviewed subtree release, independent CI, consistent command outputs and legal/IP notices.

**M5 — optional browser visualization and extensions:** offline capable browser GLB viewer and observability; no real actuation or remote-control extension in this release. External hardware would require a separate scoped specification, ownership verification and safety evaluation.

Workstreams have their own implementation tasks and test gates in the next-stage plan. A failure or deferment in Blender/3D must not block safe local JSON/terminal research or standalone packaging.

## 15. Requested design review

The selected architecture captures the user's **“all”** scope without representing a proposal as a deployed MECHA product. Reviewers should confirm that (1) both repository destinations are wanted, (2) one portable canonical engine is preferable to duplicate implementations, (3) robotics stays synthetic/read-only in the first release, (4) the user-provided Agent10 alias remains an unverified private identifier, and (5) the previously opened draft PR chain is handled with normal approval rather than auto-merging it.

**Approval stage:** This file is a **written design specification only**, not product code and not an implementation plan. After the user reviews and approves it, prepare a separate task-by-task execution plan, obtain approval for its execution method, then implement with TDD and independent PR review. **No new MECHA repository is created by this design commit.**
