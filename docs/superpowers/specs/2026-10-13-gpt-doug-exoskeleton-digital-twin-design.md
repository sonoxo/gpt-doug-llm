# GPT-DOUG-PINEAL — Physical Exoskeleton + Holographic Digital Twin Design

**Date:** 2026-10-13
**Design revision:** 1.0
**State:** PROPOSED — awaiting operator review; not an implemented or certified physical device
**Canonical repository:** sonoxo/gpt-doug-llm
**Scope:** Safety-first civilian/industrial research, single-joint bench prototype, offline simulation, interactive 3D digital twin, and optional read-only diagnostics.

> This design implements the user's chosen direction: a real physical engineering roadmap plus a holographic-style digital twin integrated with GPT-Doug. No physical exoskeleton has been fabricated, validated, fitted to a person, energized or connected to GPT-Doug. No AI-generated command controls physical actuators. "Hologram" here means a real-time rendered 3D/AR visual representation, **not** a free-space volumetric projection or a biological interface.

## 1. Intent and acceptance

The desired outcome is one canonical, reviewable, publicly visible Sonoxo engineering project that can transition from reproducible research software to a supervised physical test fixture without confusing simulation with measured reality.

Initial deliverables, in order:

1. Reproducible single-axis mechanism model with explicit units, parameter provenance and CAD exchange (STEP, DXF/3D faces, GLB, optional STL). Reuse existing PINEAL CAD source only as an architectural visual asset; do not interpret its illustrative 202-mm foundation or other decorative dimensions as certified hardware.
2. Deterministic *offline* dynamics and kinematics scenario, including independent mathematical consistency checks and explicit uncertainty labels.
3. Local, interactive WebGL three-dimensional digital twin (holographic styling) showing joint pose, travel envelope, status, measured/simulated source kind, health, and fault states. No cloud account, paid token or internet is required for use once installed.
4. Versioned, authenticated, **read-only** telemetry interface and local playback of synthetic fixtures or operator-approved recordings. No command-write transport to motors, servo drives, batteries or robots.
5. A separately reviewed physical test-rig plan for one fixture-mounted, guarded, low-voltage joint with an independent safety circuit; no wearable fitting or powered assistance during the initial release.
6. Versioned project release and optional, manually approved distribution to other owned Sonoxo repositories. No automatic organization-wide push, uncontrolled sync, silent merge or third-party infrastructure connection.

Success for v1 means a fresh macOS/Linux checkout can verify the complete synthetic scenario, render a bounded 3D model, show an induced stale or fault condition, and produce an auditable test report **without actual motor power, human participants, specialized equipment or external network**.

## 2. Current foundation verified on GitHub

- Existing merged PINEAL CAD PR #321 supplies genuine CadQuery BRep modeling and STEP, DXF, STL and GLB exporters at integrations/gpt-doug-pineal/cad/. Its README expressly says dimensions are illustrative and parts are not validated for manufacturing.
- Existing GPT-Doug memory gateway at integrations/gpt-doug-pineal/src/pineal/ offers local SQLite-backed evidence and bearer-authenticated loopback reads; do not inject telemetry into its ontology as unreviewed facts.
- The repository contains docs/superpowers/specs/2026-10-12-mecha-dual-repo-biopineal-design.md, a **proposed**, research-only MECHA dual-repository architecture. It emphasizes no hardware actuation. This design preserves that boundary and may later use a versioned read-only MECHA snapshot adapter, but does not merge, relocate, or replace the proposed MECHA implementation.
- GPT-Doug symbolic math may be used for **independently checked** algebraic verification; the existence of a solver is not evidence of a safe actuator or functioning prototype.

## 3. Alternatives and selection

| Approach | Benefit | Constraint | Decision |
| --- | --- | --- | --- |
| A. Extend PINEAL as an isolated exoskeleton engineering package | Reuse merged CAD and memory boundaries, single host CI, simple Mac install | Initial release remains a monorepo subproject | **Selected** |
| B. Place all new code directly into the unimplemented MECHA v1 proposed package | Potential future single robotics source tree | Couples the exoskeleton to unapproved MECHA dependencies and broader rollout | Defer; optional adapter only |
| C. Create a separate exoskeleton repository immediately and duplicate models | Independent branding | Duplication, drifting safety controls, difficult dependency review | Reject for initial design |

Canonical new source location **after design and implementation plan approval**: integrations/gpt-doug-pineal/exoskeleton/. The existing integrations/gpt-doug-pineal/cad/ is imported read-only as a visual asset. Do not modify the root gpt_brain runtime as a prerequisite to demonstrating offline simulator readiness. Later Sonoxo consumers import a pinned package or immutable released artifact; never copy moving HEAD into every repository.

## 4. Architecture and trust boundaries

~~~text
[Author-approved dimensional CAD parameters]  [Synthetic fixture / permitted replay]
                       |                                  |
               Geometry exporter                    Typed validation
                       |                                  |
           STEP/DXF/GLB + metadata -------+---------------+
                                         |
                         Offline joint physics / scene state
                                         |
                  signed/source-labeled snapshot contract
                                         |
                         Local 3D holographic viewer
                                         |
                            READ-ONLY diagnostics
                                         |
                   Optional GPT-Doug/PINEAL adapter
                                     (no actuation)

[Future supervised BENCH ONLY — separate approved build and test]
  encoder, limit switches, current/temp sensors
                     |
       isolated safety controller (independent MCU)
       hard-stop circuit, fault latch, watchdog, hold-to-run
                     |               |
           interlocked power     read-only event record
                     |               |
            guarded motor drive ----> local opt-in telemetry reader
                                              |
                                    digital twin (observation only)
~~~

Absolutely no connection from a language model, ontology memory writer, renderer, HTTP endpoint, CI runner, GitHub workflow, or remote user to a motor-control command interface. A future independent safety-reviewed industrial controller may perform motion only after explicit local operator action and verified bench-specific authorizations. A normal web request must never energize hardware.

## 5. Component interfaces

### 5.1 Parametric engineering model (exoskeleton/cad/)

The v1 model represents **one fixture-mounted revolute joint**, mounting plates, an illustrative linkage, a mechanical stop region and a sensor enclosure. Numeric examples are clearly marked synthetic and are not final design limits.

Inputs are a versioned, strictly typed declarative configuration with length in meters, mass in kilograms, angles in radians, joint travel limits, material reference, approximate center of mass, and a provenance object. Unsourced ratings are represented as UNKNOWN, not guessed.

Outputs: named STEP BRep solids, AutoCAD-compatible layered DXF 3D mesh surfaces, GLB named submeshes, manifest JSON, and a validation report. Any dimension, fit, thermal, clearance, stiffness, fatigue, stability or load-bearing claim must be independently assessed by qualified engineers prior to fabrication; no build-ready declaration based solely on this generator.

### 5.2 Dynamics (exoskeleton/sim/)

The baseline is a bounded classical rigid-body joint simulation. Engineering equations include:

- Required generalized torque: tau = I * alpha + m * g * l * sin(theta) + tau_f.
- Joint kinetic energy: E_k = (1/2) * I * omega^2.
- Idealized instantaneous mechanical power: P_m = |tau * omega|.
- Electrical power estimate: P_in = P_m / eta, **only** when drivetrain efficiency eta is measured or independently justified.

These are simplified engineering models, not a certified physical load case. Simulations must state assumptions for friction, gravity, torque saturation, backlash, impact, inertia, fixture rigidity, modeling error and timing. They must flag physically nonsensical parameter values, numeric blowups, nonfinite values and extrapolation outside input assumptions. No free unlimited-energy, quantum-bio-cell or biological ATP claim is permitted.

A reproducible synthetic 1-DOF fixture provides angle, velocity, acceleration, synthetic sensed torque, thermal category and explicit fault transitions. Hardware current, torque and temperature thresholds are intentionally **UNSPECIFIED** until a component BOM, bench risk analysis, vendor specifications and engineer signoff exist.

### 5.3 Snapshot and telemetry contract (exoskeleton/contracts/)

Each frame includes:

- schema_version, frame_id, monotonic sample sequence, origin_timestamp_utc, age/staleness, model_version and source_digest;
- source_kind enum: SYNTHETIC, RECORDED_AUTHORIZED, MEASURED_LOCAL_READ_ONLY;
- mode enum: OFFLINE_SIMULATION, REPLAY, BENCH_OBSERVATION;
- joint_id, position_rad, velocity_rad_s and any available force/current/temperature readings with *explicit units* and unavailable fields as null;
- safety_state enum: NOT_CONNECTED, SIMULATED, BENCH_DISARMED, BENCH_ARMED_LOCAL_ONLY, STOPPED, FAULT_LATCHED;
- human_signoff_status, calibration_status, device_id and provenance; no synthetic frame may masquerade as real measurements.

A missing, stale, future-dated, malformed, contradictory or wrong-device frame changes the viewer to UNKNOWN/FAULT; it must never mean ONLINE, ARMED or healthy by default. Recorder/replay input has bounded size, count, rate, timestamp drift, and serialization. All event logs are bounded and scrubbed of private names, credentials and device secrets.

### 5.4 Digital twin (exoskeleton/viewer/)

The browser-based 3D renderer uses the same versioned model and snapshot contract as the simulator. Support orbit, exploded layers, labeled joints, simulation playback, mode and timestamp badges, and a conspicuous safety/fault panel. WebGL is a visualization: the project does not claim a physical volumetric hologram or fabricated hardware.

Default launches locally, works offline after installation, and has no mandatory login or cloud access. No camera, microphone, network scan or health data collection occurs without explicit operator authorization. No pointer action or 3D widget can command a motor.

### 5.5 Safety and future physical bench rig (exoskeleton/safety/)

**Independent hardware safety controller**, not GPU/LLM software, owns state transition and power enable. Design default is an unpowered, disconnected test fixture. Physical plan must include mechanical guarding and fixture anchoring, travel stops, fused low-voltage supply, appropriately designed hardwired emergency stop/power isolation, loss-of-communications behavior, independent limit sensing, current/temperature monitoring, watchdog timeout, no automatic restart and signed local hold-to-run protocol.

Exoskeleton geometry and control are not to be mounted on a human in early phases. Specific motor choice, power rating, material, gearing, load capacity, speed and maximum joint torque are deliberately undefined until independent hazard analysis and hardware design review. A bench safety controller must not consume remotely provided task instructions as actuation authority. Hardware-specific firmware requires a **separate future written specification and reviewed implementation plan**; no live firmware or power-enabling logic is included in v1.

### 5.6 GPT-Doug and ZYRA/PINEAL (exoskeleton/adapters/)

Optional read-only adapters report synthetic and approved local evidence, numerical anomalies, physics diagnostics and audit verification. They may propose a **human-readable** engineering observation for operator review, not a motion command. The ontology treats unsourced observations as tentative until reviewed; a memory confidence score, agent role, or GitHub merge cannot grant safety approval.

No brain stimulation, reading thoughts, human cell creation, actual military system integration, weapon actuation, autonomous targeting or civilian/medical performance claim is in scope.

## 6. Security and data rights

- All defaults offline and read-only; any API binds 127.0.0.1 with bearer authentication and no permissive CORS. Viewer assets load from local files/server. No surprise telemetry uplink.
- Secrets stay in operator-local environment/OS secret store; never put keys in logs, manifests, artifacts, PR bodies, fixtures or committed code.
- Only allowlisted, bounded numeric observations are accepted; arbitrary strings from replay are not commands, executable plugins, endpoints, file paths, shell text or embedded HTML/JS.
- Public GitHub artifacts contain synthetic examples and safe mechanical abstractions only. No actual user medical/EEG information, CUI/classified files, private security telemetry or human identity.
- Source and data-rights provenance travel with every exported model; external patents referenced for research do not confer fabrication rights or freedom to operate.
- Signed and pinned releases are recommended for downstream consumers. Neither published documentation nor hash digests alone establishes physical system certification or an authenticated identity.

## 7. Global Sonoxo integration and distribution

"Push updates globally" means **publicly accessible reviewed GitHub source and an opt-in, version-pinned integration contract for authorized Sonoxo repositories**. It does not mean issuing commands to machines globally, accessing unauthorized systems, silently merging to main, changing every repository, or opening a globally reachable motor API.

1. Draft this specification on a dedicated feature branch and open a PR against sonoxo/gpt-doug-llm/main for review.
2. After operator approval of the spec, prepare and seek approval of a detailed implementation plan. No production code is in this design-only PR.
3. Implement modular software in one canonical subtree with CI gates: unit, physics bounds, CAD shape validity, GLB viewport smoke, schema fuzz/property tests, and safety-regression tests.
4. Post-GitHub PR review, selectively merge through existing branch protection policies. A broken unrelated gate must be diagnosed, not bypassed.
5. Tag a reviewed release, generate checksummed artifacts, and publish canonical install directions. Consumers explicitly opt in to that immutable version. Any owned downstream repository must have its own compatibility checks and authorized PR. No unrestricted fanout token or auto-push.
6. Physical build artifacts are **engineering drafts only**, not warranty, certification, medical approval or ready-to-wear instruction sets.

## 8. Acceptance and verification gates

| Gate | Condition | Evidence |
| --- | --- | --- |
| G0 Design | Operator reviews this written spec and implementation plan; resolves research application and scope | Approved versioned GitHub review |
| G1 Simulation | Offline deterministic fixture produces 60 repeatable frames without hardware dependencies; invalid parameters fail | macOS/Linux tests and reproducible digest |
| G1 Safety | Unconnected/hardware-disabled default; no call path from LLM/WebGL/HTTP to motor output; stale/disconnect/fault rendered accurately | Static checks, forbidden-import checks, fault-injection tests |
| G1 Viewer | Reads actual GLB geometry and source-labeled frames, supports rotate and replay in local browser, shows unverified provenance | Browser-to-data smoke test with synthetic fixture |
| G1 Packaging | Reproducible local Mac CLI, lock/dependency policy, no paid services, no network on demo | CI and offline installation validation |
| G2 CAD Bench | Engineer signs off on joint model, material/load/clearance analysis, mechanics and risk assessment, procurement rights | Reviewed design dossier (no human fitting) |
| G3 Physical Bench | Separately approved independent safety controller and secured fixture are inspected, E-stop and fault handling are tested, operator supervises low-energy commissioning | On-site signed safety-test record |
| G4 Wearable Research | New hazard analysis, human-subject/medical review where applicable, ergonomics and emergency extraction design, insurance/regulatory review | Separate new design and explicit go/no-go authorization |

No G1 software pass implies G2–G4 success or permission to energize a physical suit.

## 9. Implementation task decomposition for later plan

- M1: Schema/provenance contracts, denial-by-default fixture load, independent safety state logic for **simulation only**.
- M2: Parameterized one-axis joint generator + GLB/STEP/DXF exports + CAD validity checks.
- M3: Deterministic offline physics with real unit conversions, bounded assumptions, and failure-mode tests.
- M4: Local browser WebGL digital twin and test fixtures; real/replay source labels and fault UI.
- M5: Read-only loopback telemetry and optional GPT-Doug/PINEAL diagnostics, no control side effects.
- M6: CI, Mac setup, version manifest, operator runbook, and gated downstream release process.
- Later, separately approved: Physical fixture drawings, BOM/risk review, MCU safety controller, hardware-in-the-loop characterization. NOT a dependency of synthetic demo readiness.

## 10. Rulings and unresolved choices

- **Ruling — purpose:** The user selected physical exoskeleton + holographic twin but did not identify a body joint or regulated use case. Select **civilian/industrial laboratory single-joint bench research** for the first design because it has a controlled load path, avoids unauthorized human trials and creates reusable joints/simulation foundations. If later changed to mobility assistance or rehabilitation, first amend this specification and safety requirements.
- **Ruling — hologram:** Use WebGL/AR-like 3D rendering for v1; do not promise actual volumetric holography or brain-computer links.
- **Ruling — global distribution:** Public GitHub branch and reviewable release architecture, not indiscriminate changes to all Sonoxo repositories or remote hardware access.
- **Ruling — implementation boundary:** Existing PINEAL CAD remains a conceptual upstream reference, not validated mechanical measurements. Any measured physical ratings require independent evidence.

**Review request:** Verify that the initial industrial-research, single-joint, non-wearable, read-only digital-twin milestone matches the intended foundation. Written implementation planning begins only after this document is reviewed and approved.
