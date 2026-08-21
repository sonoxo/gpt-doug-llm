# ZYRA Agentic Runtime

This document defines the operating model for ZYRA's bounded autonomous coding system.

## Purpose

The Agent Core exists to turn a natural-language engineering goal into a finite, inspectable repository mission.

It is not intended to be an unrestricted machine-control layer. Its autonomy comes from **closed-loop planning and verification inside a constrained capability envelope**.

## Default mission budget

```text
max steps:       8
max wall time:   240 seconds
max model calls: 12
scope:           current repository
```

Budgets are deliberately finite. Reaching a budget ends the mission instead of recursively extending it.

## Mission modes

### `/plan <goal>`
Produces a bounded plan without applying mission changes.

### `/do <goal>`
Runs a normal repository coding mission.

### `/evolve <goal>`
Runs a self-improvement mission limited to ZYRA/agent/core/test surfaces. Evolve mode uses the same checkpoint, validation, budget, and rollback controls as normal missions.

## Mission state

Each mission records:

- unique mission ID;
- goal;
- mode;
- start/finish time;
- step events;
- touched files;
- validation checks;
- rollback state;
- summary/error.

This makes the autonomous path easier to inspect than a hidden one-shot script.

## Tool philosophy

The Agent Core uses small, explicit tools instead of unrestricted shell access.

Typical capabilities include:

- list/search repository content;
- read allowlisted text/code files;
- create or replace allowlisted repository files;
- checkpoint files before modification;
- run predetermined validation checks;
- restore checkpointed content.

The tool boundary rejects repository path escapes and avoids sensitive host directories.

## Write transaction model

```text
1. Resolve repository path
2. Validate path + file type
3. Capture checkpoint
4. Apply mission-owned write
5. Record touched file
6. Run validation
7. Review mission result
8a. PASS → keep changes
8b. FAIL → restore checkpoint
```

The intended property is **reversibility**. Autonomous editing should not turn one bad model response into a permanent repository mutation.

## Reviewer behavior

Reviewer output is expected to be structured. If a reviewer response is malformed, the orchestration layer may make one bounded repair attempt to normalize it. Repeated malformed output stops rather than creating a repair loop.

## Interaction with LASER

LASER protects ZYRA's model-processing path. The Agent Core protects repository mutation.

These systems solve different problems:

| Layer | Protects | Primary response |
|---|---|---|
| LASER | Interactive/model path | Intercept or isolate |
| Agent Core | Repository mutation | Reject, validate, rollback |
| Self-Heal | Local model runtime | Repair once, then stop |
| CI Security Gate | Shared branch quality | Pass/fail independent checks |

## External actions

The local Agent Core intentionally does not expose unrestricted tools for:

- `git push`;
- cloud deploys;
- sending messages;
- arbitrary network requests;
- offensive scanning/exploitation;
- credential harvesting;
- arbitrary shell execution.

External integrations can exist elsewhere in the project, but they should remain explicit integration boundaries rather than implicit powers of every autonomous mission.

## Reliability targets

Future Agent Core evaluation should measure:

1. task completion rate;
2. rollback correctness;
3. false-success rate;
4. validation coverage;
5. average model calls per successful mission;
6. time-to-recovery after model/runtime failure;
7. percentage of missions requiring human correction;
8. reproducibility across repeated runs.

## North-star principle

**Increase useful autonomy by improving planning, tools, tests, and observability—not by removing the controls that make autonomous execution trustworthy.**
