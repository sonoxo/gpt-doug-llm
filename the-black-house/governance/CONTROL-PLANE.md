# THE BLACK HOUSE — Control Plane Boundary

## Purpose

The Black House coordinates mission identity, routing, policy, execution evidence and operational health across the Sonoxo ecosystem. It is the control-plane root, not a replacement for the source repositories that implement Zyra, XUNIA, VA3LM, Wakeup3lm, NXYZ or external adapters.

## Execution boundary

1. A mission enters through the RVIA mission contract.
2. SHADOW GLASS validates identity, provenance, requested capability and policy scope.
3. Planning may be performed by GPT-DOUG-MAX, VIRGINIA or Wakeup3lm.
4. Consequential mutation remains gated by ZYRA approval and the native service authorization layer.
5. XUNIA, NXYZ, Zyra Cloud or another registered adapter may execute only within its declared capability boundary.
6. GLASS ONION records observable execution evidence.
7. The Black House records the resulting mission state and health evidence.

## Runtime truth rules

- A passing unit test does not by itself prove a live runtime.
- A live process does not by itself prove an authorized external integration.
- A repository adapter does not imply access to an external tenant.
- A failed required CI or runtime health gate makes that component RED.
- An unverified external tenant is AMBER, not GREEN.
- No component may self-promote from implemented to deployed without deployment evidence.

## Required Phase 1/2 gates

- VA3LM: tests, Ruff, Bandit, compile and port-8088 `/healthz` smoke.
- XUNIA: TypeScript build, root AVA suite and native resilience-atlas Node suite.
- Zyra: main CI.
- Black House root: registry, mission schema, ontology and runtime-contract validation.

## Authority

`the-black-house/` is canonical for control-plane contracts. Source code remains canonical in each registered implementation repository.
