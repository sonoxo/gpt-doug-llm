# MECHOPS // Autonomous Warehouse Digital Twin

**Date:** 2026-10-13  
**Status:** Simulation and UI prototype; hardware disconnected  
**Parent ecosystem:** GPT-DOUG-LLM MAX / ZYRA / ontology-first governed execution  
**App:** https://lovable.dev/projects/2b6aa2e4-67d8-48a3-8fd9-7083c7772746  
**Preview:** https://id-preview--2b6aa2e4-67d8-48a3-8fd9-7083c7772746.lovable.app

## Mission and bounded automation

Design a warehouse where robots carry routine material-handling work and **humans retain authority** as operators, supervisors, mechanics and voluntary assisted-lift/exoskeleton personnel. "Mechs" means authorized industrial assistive systems and remote/vehicle operator stations, not people forced to act as machines.

The human-commanded system handles receiving, slotting, picking, packing, dispatch, charging and inspection. The software must show moving robots and actionable alarms without pretending that simulated state is physical telemetry.

The core execution rule matches the host repository: **AI proposes -> ontology grounds -> safety policy constrains -> human approves high-risk operations -> adapter dispatches -> observed evidence is logged**. Model generated instructions cannot override protective equipment, PLCs, interlocks or E-stops.

## Architecture / dataflow

```text
PUBLIC READ-ONLY SOURCES                 PRIVATE OPERATIONAL ENVIRONMENT
NASA EONET | CelesTrak metadata          ERP/WMS | robot OEM APIs | cameras
               |                                    |
          provenance filter                scoped identity and edge gateway
               |                                    |
               +---------> EVENT BUS <--------------+
                              |
                  typed evidence / ontology
                              |
            +-----------------+------------------+
            |                 |                  |
       digital twin      dispatch policy    safety supervisor
       state & replay    A* and heuristics  human-zone / E-stop
            |                 |                  |
            +------------ command UI ------------+
                              |
                   named operator approval
                              |
                    gateway command adapter
                              |
                 independently safety-rated PLC
                 / OEM protective robot controls
```

### Capability boundary

| Layer | Demonstrable in this deliverable | Production dependency |
|---|---|---|
| Floor twin | Animated warehouse grid, racks, stations, robot route trails | Surveyed floor map, calibrated frames, robot physical envelopes |
| Agent operations | Simulated robot fleet, task dispatch, queue lifecycle | OMS/WMS auth, robot-vendor fleet adapter |
| Human operations | Human approval and simulated restricted zones | OSHA/local safety design and independent safety hardware |
| Quantum Lens | Classical simulated annealing + A* comparisons | Evidence of benchmark advantage; **no quantum processor claimed** |
| String Lens | Educational graph visualization | Not an accepted robotic physics control system |
| Orbital/data | Public NASA EONET read-only query; CelesTrak public GP reference | Network allowlists, source validation, operational relevance |
| Global network | Explicit connector registry; all initially not configured | **Cannot access all computers, satellites, or networks**; opt-in auth per owner |
| Analytics | Event-derived metrics and provenance | Persistent timeseries, event bus, clock sync, telemetry quality review |
| Safety stop | Software simulation motion halt, named acknowledge | Physical safety-rated E-stop independent of this web UI |

## Ontology entities

- `Robot`: `id`, `kind`, `position`, `battery_pct`, `mode`, `current_task_id`, `telemetry_observed_at`, `source`.
- `Task`: `id`, `kind`, `pickup`, `dropoff`, `priority`, `risk_class`, `status`, `assignee_id`, `approval_id`.
- `HumanOperator`: `subject_id`, `role`, `availability`, `authorized_scope`. No biometric collection.
- `Zone`: `id`, `polygon`, `risk_class`, `occupancy`, `access_policy`.
- `StockItem`, `Shelf`, `InventoryMovement`, `Order`: provenance-linked inventory.
- `Approval`: `actor`, `role`, `action`, `reason`, `time`, `signature` (in production).
- `SourceEvidence`: `source_uri`, `observed_at`, `quality`, `trust_level`, `sha256`.
- `Event`: `id`, `type`, `actor`, `source`, `payload`, `time`, `trace_id`.

**Event rule:** every UI tile must say whether values are `SIMULATOR`, `PUBLIC_SOURCE` or `VERIFIED_EDGE_TELEMETRY`. A failed feed becomes `UNAVAILABLE`, never silently synthesized.

## Simulator acceptance requirements

1. At least 12 distinct mobile units; all motion derives from a clocked deterministic model.
2. A* routes avoid nonwalkable shelving and active human proximity zones.
3. Collision reservation prevents units sharing the same grid cell in a single tick.
4. Submitted tasks pass from `queued` to `assigned`, `in_progress`, and `completed`.
5. High-risk lifts, unlocks and maintenance require a **named human** approval.
6. The UI E-stop freezes the **simulated** fleet and must never be described as a safety-rated device.
7. Route optimization outputs documented inputs, objective function and route costs. Quantum-inspired methods are classical heuristics.
8. Event log exports JSON/CSV snapshots, including provenance, UTC timestamps and clear source/status.
9. No external MQTT, OPC UA, ROS, WMS or satellite command connections are initiated by default.
10. Simulation can be replayed/reset, and autonomous planning cannot affect real equipment without integration review.

## Production readiness gates

- Threat model: network boundaries, robot identities, signed commands, replay prevention, egress controls, secret storage, operator audit, least privilege and rollback.
- Independent safety engineering: functional safety allocation, safe-stop latency, worker proximity, speed/force limits, obstacle detection, power/network failures and manual recovery. See ISO 3691-4:2023, applicable worker-safety law and OEM documentation. **This prototype is not certified.**
- Edge integration: ROS 2 / Open-RMF fleet adapter only with OEM sign-off, hardware-in-loop test plan and command allowlist; OPC UA/MQTT access authorized by owners.
- Reliability: rate limits, persistent event log, queue idempotency keys, job timeouts, telemetry freshness windows, watchdogs and emergency incident response.
- Data governance: license/terms, NASA source disclaimer, source update cadence, no exaggerated satellite accuracy, operator privacy.

## Technical references

- Open-RMF fleet adapter: https://github.com/open-rmf/rmf_ros2/blob/main/rmf_fleet_adapter_python/README.md
- NASA EONET v3: https://eonet.gsfc.nasa.gov/docs/v3
- CelesTrak GP: https://celestrak.org/NORAD/documentation/gp-data-formats.php
- ISO 3691-4:2023: https://www.iso.org/standard/83545.html

**Verification disclaimer:** A web simulation is not a deployed warehouse, physical exoskeleton, quantum computer, universal network connection, or commissioned industrial control system.
