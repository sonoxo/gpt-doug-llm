# GPT-DOUG // XUNIA ASTRAL GRID v2

**Public home:** https://xunia.org/xuniaverse  
**Astral console:** https://xunia.org/astral  
**Project grid:** https://xunia.org/projects  
**GPT-DOUG node:** https://xunia.org/projects/gpt-doug-llm

Astral Grid is the governed resource-orchestration layer for GPT-DOUG inside XUNIA. It models compute, memory, context, storage, network headroom, dependency health, authorization, zone boundaries, and lease state as an explicit resource graph.

## v2 control loop

```text
REQUEST
  ↓
TARGETED STATE ACQUISITION
  ↓
POLICY + AUTHORIZATION
  ↓
RESOURCE SNAPSHOT
  ↓
ZONE / LABEL / DEPENDENCY VALIDATION
  ↓
PRIMARY SCORING
  ↓
ATOMIC RESERVATION
  ↓
OPTIONAL BOUNDED PEER ASSIST
  ↓
EXECUTION
  ↓
VERIFY
  ↓
DEPLETION CHECK
  ├─ healthy → RELEASE / ARTIFACT
  └─ depleted → REBALANCE OR FAIL CLOSED
  ↓
TAMPER-EVIDENT AUDIT
```

## What changed in v2

1. **Multi-resource admission control** — tasks request named resources instead of one scalar capacity value.
2. **Primary/non-shareable separation** — sensitive or stateful resources can be required to remain on the primary node while explicitly shareable resources can be pooled.
3. **Atomic reservations** — every reservation is checked again before state changes, reducing partial-allocation failure modes.
4. **Lease-based execution** — reservations expire and release rather than becoming permanent hidden load.
5. **Depletion-aware rebalance** — unhealthy or low-headroom primaries can trigger a new authorized route.
6. **Quarantine and dependency gates** — quarantined, unauthorized, unhealthy, or dependency-failed nodes are excluded automatically.
7. **Zone-aware containment** — tasks can stay inside a declared software trust/containment zone.
8. **Hash-chained audit records** — every event carries a previous-record hash and can be verified as a chain.
9. **XUNIA-first identity** — public discovery stays on xunia.org while GitHub remains the backing source layer.
10. **Fail-closed semantics** — depletion, capacity loss, authorization loss, or dependency failure never silently degrades into ungoverned execution.

## Research-derived software abstractions

The uploaded research materials are used only as high-level architectural inspiration. They are not copied as physical-control implementations.

- **US20260270734A1** → software abstraction: monitor depletion, locate eligible peers, request bounded assistance, and continue only if the task can still be completed under constraints.
- **US20260269610A1** → software abstraction: controller-mediated transfer request, eligibility decision, then execute-or-deny.
- **US12724802B1** → software abstraction: acquire missing state, preprocess, validate, apply guardrails, and emit a structured decision.
- **US20260264028A1** → software abstraction: staged containment, separation boundaries, and controlled interfaces between processing stages.

## Core invariants

```text
NO AUTHORIZATION → NO ROUTE
NO HEALTH → NO ROUTE
DEPENDENCY NOT READY → NO ROUTE
QUARANTINED → NO ROUTE
NON-SHAREABLE RESOURCE DOES NOT FIT PRIMARY → NO ROUTE
INSUFFICIENT AUTHORIZED CAPACITY → NO ROUTE
DEPLETED PRIMARY → REBALANCE OR FAIL CLOSED
EVERY STATE CHANGE → AUDIT RECORD
```

## Files

- `grid.py` — dependency-free Python v2 reference scheduler.
- `xunia-grid.json` — canonical public-route, policy, research-lineage, and orchestration contract.
- `test_grid.py` — standard-library regression tests for peer assist, containment, fail-closed gating, leases, and audit-chain integrity.

## Run locally

```bash
python astral/grid.py
python -m unittest astral/test_grid.py -v
```

## Truth boundary

`ASTRAL`, `GPT-DOUG`, `XUNIA`, `ZYRA`, `Glass Onion`, `Black House`, `Green House`, `RVIA`, and related names are project/software architecture labels. Patent references are research lineage only. This module does not claim external government, military, vendor, standards-body, certification, or operational authority, and it does not expose autonomous real-world actuation.
