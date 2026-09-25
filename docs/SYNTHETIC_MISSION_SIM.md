# ZYRA / XUNIA Synthetic Mission Simulation

Status: **simulation and training only**.

This sandbox extends the Maven-style mission support workbench with a deterministic, replayable scenario engine. It uses an abstract 20x20 integer grid and synthetic entities only.

## What it models

- allied, opposing, and neutral synthetic entities;
- sensors, mobile assets, hazards, and protected zones;
- deterministic step-by-step movement on an abstract grid;
- confidence and quality metadata;
- proximity-based safety alerts around protected zones;
- analyst-facing recommendations: `OBSERVE`, `SHIELD`, `EVACUATE`, `HOLD`, or `REPOSITION`;
- replay history for every simulation tick;
- Maven/Foundry-friendly `Scenario` summary events;
- human review before any recommendation is treated as a decision.

## What it does not model

The engine deliberately rejects real-world coordinates, identity tracking, weapon or munition parameters, aimpoints, impact/intercept points, guidance/seeker fields, fire-control fields, targets, or external actuation commands.

There is no live sensor connector and no external executor in this module.

## Control loop

```text
SYNTHETIC SCENARIO
      |
      v
NORMALIZE + VALIDATE
      |
      v
ABSTRACT GRID STATE
      |
      v
DETERMINISTIC TICK
      |
      v
SAFETY ASSESSMENT
      |
      v
HUMAN REVIEW QUEUE
      |
      v
MAVEN SCENARIO EVENT + REPLAY HISTORY
```

## Python example

```python
from agents.synthetic_mission_sim import run_simulation, sample_scenario

result = run_simulation(sample_scenario(), ticks=6)
print(result["assessment"])
print(result["history"])
```

The bundled fixture starts one synthetic hazard several grid cells away from a protected zone. Each tick advances the fixture by one abstract cell, records the state, recomputes a safety score, and emits a recommendation for analyst review.

## Invariants

- `syntheticOnly` must be `true`.
- Grid values are bounded to `0..19`.
- Simulation runs are bounded to `1..100` ticks per call.
- Recommendations remain `PENDING_HUMAN_REVIEW`.
- `automaticExternalAction` is always `false`.
- Maven simulation events declare `externalActuation: false` and `realWorldCoordinates: false`.
- Restricted fields fail closed, including when nested in metadata.

## Relationship to existing ZYRA components

The sandbox complements:

- `agents/mission_support_workbench.py` for evidence fusion and analyst review packets;
- `docs/maven-ontology/ontology.json` for Maven/Foundry object relationships;
- `va3lm/src/va3lm/od_plane.py` for synthetic / owned-lab simulation controls.

It can be rendered in XUNIA as a training replay layer without turning the simulation state into a real-world control surface.
