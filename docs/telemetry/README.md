# CL1 TELEMETRY ATLAS / LINEAR × KINETIC × ONTOLOGY

**Public route after GitHub Pages deploy:** https://xunia.org/telemetry/

This is a new free, interactive observability surface for GPT-DOUG-LLM / XUNIA:
three synchronized browser-canvas views driven by the same local
`PhysarumModel`. The source is the existing
`../physarum/model.js` and `../physarum/ontology.json`.

This is **simulation telemetry**, not measured neuronal activity, living-cell
biophysics, brain interfaces, a sensor feed, or physical device control.

## Visual instruments

| Plane | Implementation | Source and limits |
| --- | --- | --- |
| **LINEAR** | Line plot over solver step index, hover/keyboard sample cursor, selectable metric and auto scaling | Local deterministic model time-series, not wall-clock sensor samples |
| **KINETIC** | Animated moving particles and directional arrowheads on the 216-node / 402-edge transport graph, with editable nutrient/barrier grid | Arrow direction = sign(Q), relative particle speed follows \\|Q\\|. It is not physical velocity, acceleration or actuated motion |
| **ONTOLOGY** | Selectable 16-node, 17-link typed Physarum graph, curated biological nodes versus synthetic model nodes, research citation inspector | Existing `Physarum` ontology; no inferred physical neural connections |

**Seven source-qualified model metrics** are declared in
[`registry.json`](./registry.json):

1. `flux`: sum of absolute signed edge fluxes, Σ |Q|.
2. `tubes`: count of usable edges with conductivity D ≥ 0.26.
3. `conductance`: arithmetic mean of unblocked edge D.
4. `energy`: sum of Q², an index—not joules.
5. `motion`: mean |Q| per edge, a movement **display proxy**, not m/s.
6. `delta`: discrete difference in total |Q| between recorded steps, **not physical acceleration**.
7. `pressure`: model max/min pressure range, not pascals.

All values are **dimensionless or model iteration units**, and contain explicit
`SIMULATED` / `DERIVED_SIMULATION` evidence labels. Chart selection changes
its y-axis scale; it does not mix metrics with different units into a single
uninterpretable scale. The timeline stores a bounded 240 samples in memory.

## Work with the model

At https://xunia.org/telemetry/ change the instrument focus, select a metric,
play/pause the model, edit food and barriers, adjust the reinforcement/decay
parameters, inspect source-linked objects, and capture a kinetic canvas PNG.

Press **Cmd/Ctrl+K** to open the safe local command line:

```text
/metric flux
/step 40
/wall 8 6
/food 15 4
/focus ontology
/select tubules
/metric motion
/health
```

Other supported commands: `/metric tubes|conductance|energy|delta|pressure`,
`/focus all|kinetic|linear|ontology`, `/pause`, `/play`,
`/reset`, `/export csv`, `/export json`. The console is a finite
local UI parser, **not a system shell**.

### Export

- **LINEAR CSV:** single header and chronological step/metric rows.
- **ONTOLOGY JSON:** model timestamps (iteration indices), source evidence,
  metric schema, available topology and 240-sample bounded history.
- **KINETIC PNG:** rendered canvas snapshot.

All exports are initiated by a click or local command, in the browser;
no third-party account, telemetry service or external storage is required.

## Run on Mac (free)

```bash
cd ~/xunia-xenology-live && git pull --ff-only && bash scripts/xunia-cosmos
```

Use the printed localhost port and open `/telemetry/`. If your local
server is still listening on 8873, use
`http://127.0.0.1:8873/telemetry/`.

## Evidence and integrated brain

The ontology canvas reads the *same*
[`Physarum` source graph](../physarum/ontology.json) as the previous
Forge feature and preserves evidence distinctions between biological
observations and synthetic models. Research references:
[Tero et al. 2007](https://pubmed.ncbi.nlm.nih.gov/17069858/),
[Tero et al. 2010](https://pubmed.ncbi.nlm.nih.gov/20093467/), and
[Reid et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3491460/).

The `gpt_brain/telemetry.py` local source registry and BrainKernel hook
provide metric definitions and provenance for explicitly relevant
telemetry or kinetic-flow prompts; they do not retrain the language model
or fetch external sensors. XUNIA HQ, Physarum Forge, Synapse, Fusion and
Biological Data Center all link to the telemetry atlas.

## Verification

```bash
node --check docs/telemetry/engine.js
node --check docs/telemetry/atlas.js
node tests/xunia_telemetry_model_smoke.js
python3 -m unittest discover -s tests -p 'test_xunia_telemetry.py' -v
python3 tests/xunia_telemetry_chrome_smoke.py
```

The existing free COSMOS CI runs Node numerical tests and Python/Chromium
integration tests on Python 3.11 and 3.12, including reduced-motion
accessibility. Animation automatically pauses when the tab is hidden, and
respects OS reduced-motion preference at launch.

**Boundary:** Kinetic = visualization of modeled directional flux. This is
not a hardware actuator, weapon, real neural interface, calibrated
biophysics, or claimed physical velocity measurement.
