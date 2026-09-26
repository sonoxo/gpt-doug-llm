# GPT-DOUG / GPT-CHAOS Patent Learning Batch — 2026-09-17

Status: research ingestion + safe architecture generalization  
Scope: public patent publications surfaced from USPTO Patent Public Search  
Doctrine: **learn broadly, promote narrowly, test before adoption, never silently self-modify**

## Canonical learning loop

```text
DISCOVER
  -> VERIFY PUBLICATION + SOURCE DEPTH
  -> EXTRACT ARCHITECTURE
  -> GPT-CHAOS CRITIQUE
  -> SAFETY / IP / POLICY FILTER
  -> SANDBOX
  -> TEVV
  -> HUMAN-APPROVED PROMOTION
  -> MONITOR
  -> ROLLBACK IF REGRESSION
```

No title, abstract, search hit, or patent publication is treated as permission to copy proprietary implementations. External legal status, licensing, patent scope, and project adoption remain separate fields.

## Research set

| Publication | Title | Evidence depth | Safe project lesson | Status |
| --- | --- | --- | --- | --- |
| US20260280758A1 | Dynamic code block bundle interleaving | abstract + description | Dynamically size work bundles from channel/resource constraints; use bounded interleaving to trade throughput, diversity, memory, and latency | CANDIDATE |
| US20260279020A1 | System and method for generating AI training image data for autonomous driving | abstract | Synthetic-data pipeline: derive structural masks/edges, then style-transform for training; simulation/data generation only | CANDIDATE_SIM_ONLY |
| US20260279077A1 | Electronic device and method of operating the same | abstract | Extract object features with a neural model, track across later frames, and emphasize detected regions for visual QA/attention | CANDIDATE |
| US20260281456A1 | Image encoding/decoding method and device, and recording medium on which bitstream is stored | metadata only | Keep in codec/compression research queue until full claims/description are reviewed | RESEARCH_QUEUE |
| US20260280121A1 | Antenna device | abstract + description | Treat communications hardware as a constrained subsystem; record energy/cost/beam-flexibility tradeoffs rather than assuming one beamforming path | RESEARCH_ONLY |
| US20260274292A1 | Autonomous driving vehicle | abstract/summary | Temporal trajectory-following ideas may inform simulation and state-estimation tests; never translate directly into live vehicle control without dedicated safety engineering | SIMULATION_ONLY |
| US20260276397A1 | Generating drivable paths for lanes | metadata only | Safety-critical path-generation research target; no implementation until full source review and simulation TEVV | RESEARCH_QUEUE |
| US20260278446A1 | Hybrid quantum-classical control of an artificially intelligent entity | abstract + description | Prediction-error threshold -> escalate from primary predictor to independent alternate solver; feed verified corrections back into training. For GPT-DOUG this becomes critic/human escalation, not direct actuator authority | CANDIDATE |
| US20260277242A1 | Last-mile delivery robot and method | abstract + description | State-machine design, obstacle-aware navigation concepts, remote takeover, explicit unload states; simulation/robotics research only | SIMULATION_ONLY |
| US20260277241A1 | Parcel delivery method, using a delivery van and at least one delivery robot | abstract + description | Dock/undock lifecycle, battery/maintenance constraints, teleoperation fallback, status-aware mission handoff | SIMULATION_ONLY |
| US20260277568A1 | Accessing memory using memory accelerators | abstract + description | Compiler/runtime can map declared memory-layout intent to supported accelerator instructions while hiding hardware-specific syntax | CANDIDATE |
| US20260277787A1 | Generating data structures to use memory accelerators | abstract + description | Compiler-generated descriptors/data structures can bridge high-level transfer intent to memory-accelerator execution | CANDIDATE |
| US20260277569A1 | Tile program optimization using sub-tiles | abstract | Hardware-aware sub-tiling + ordered execution can improve accelerator scheduling; map to bounded task chunking and memory-aware worker scheduling | CANDIDATE |
| US20260276358A1 | Safety device and method for weapons | abstract + description | **SAFETY-ONLY EXTRACTION:** independent preconditions, time-limited readiness, fail-safe reversion, and separation of sensing/authorization/action. Do not adopt weapon actuation, payload, detonator, targeting, or employment mechanisms | SAFETY_PATTERN_ONLY |
| US20260277170A1 | Systems and methods for an automation ecosystem | abstract + description | Versioned routine IDs, explicit trigger conditions, distributed local copies, central initiation, device-local execution, and post-execution status convergence | CANDIDATE |

## Hard-wired GPT-DOUG upgrades

1. **Prediction-error escalation** — compare expected vs observed state; crossing a configured threshold routes the task to GPT-CHAOS, an independent solver, or a human gate.
2. **Resource-aware chunking** — choose work-bundle/sub-tile size from latency, memory, cost, and model/tool limits.
3. **Memory-accelerator abstraction** — represent memory movement as typed intent; compile only into supported backends.
4. **Distributed routine identity** — automation routines require stable IDs, versioning, triggers, target scopes, and post-run status evidence.
5. **Visual object continuity** — keep object identity/features across frames for multimodal QA and scene consistency.
6. **Simulation-first autonomy** — autonomous driving, delivery robotics, lane/path planning, or physical embodiments stay in simulation until an independent physical-safety program exists.
7. **Weapon-source isolation** — weapon-related public sources may contribute only generic fail-safe/interlock concepts. Weapon-enabling details are excluded from the learning promotion path.

## Hard-wired GPT-CHAOS critic questions

- Is the source depth sufficient for the claimed lesson?
- Is the lesson a general engineering principle or a proprietary implementation detail?
- Could the proposed adoption create an unsafe physical-control path?
- Does the plan preserve human override, stop conditions, and rollback?
- Does the proposal rely on a capability the current runtime does not actually have?
- Are uncertainty and conflicting evidence preserved?
- Does any source involve weapon operation, targeting, payload actuation, or other harmful mechanisms? If so, restrict extraction to generic safety architecture.
- Has a candidate survived sandbox + regression + provenance checks before promotion?

## Persistence rule

This repository record is the durable project memory. Chat/model weights are not silently modified. A candidate becomes canonical only through a versioned code/config change with provenance and tests.
