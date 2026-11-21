# CL1 PHYSA-01 / PHYSARUM FORGE

**Public intended URL:** https://xunia.org/physarum/

A source-linked, free, browser-only **Physarum polycephalum** network
physicalization and adaptive-routing laboratory for GPT-DOUG-LLM, XUNIA and
CL1. It models decentralized routing and produces downloadable design
blueprints. It does **not** contain live organisms or control lab hardware.

## The biological organism

*Physarum polycephalum* (“The Blob”) is a slime mold in **Amoebozoa**,
a group of amoeboid eukaryotes distinct from fungi. In its macroscopic
plasmodium stage, it is one giant cell with many nuclei sharing cytoplasm
and connected by network-like tubes. Protoplasmic streaming conveys nutrients
and signals throughout the living plasmodium.

Published experimental findings include efficient pathfinding and network
adaptation, tube reinforcement/decay, chemical foraging, and effects of
external slime trails on navigation. These are examples of **non-neural,
decentralized adaptive behavior**, sometimes called biological intelligence.
There is no evidence that this organism has a conventional brain, neurons, an
electronic network interface or human-like consciousness.

**Research sources in** [`ontology.json`](./ontology.json) with typed links:

- [Tero, Kobayashi & Nakagaki, J. Theor. Biol. (2007)](https://pubmed.ncbi.nlm.nih.gov/17069858/) – adaptive network model.
- [Tero et al., Science (2010)](https://pubmed.ncbi.nlm.nih.gov/20093467/) – biological network design and transport robustness.
- [Reid et al. (2012), PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3491460/) – extracellular slime trails and spatial memory.
- [Cognition review (2023), Animal Cognition](https://link.springer.com/article/10.1007/s10071-023-01782-1) – evidence and interpretation limits.
- [Flow-network adaptation review](https://www.sciencedirect.com/science/article/pii/S1754504823001022) – transport feedback and behavior.

## Interactive tools

The canvas contains an original 18 × 12 graph: **216 virtual nodes and 402
initial possible tubes**. Place up to eight food sources, paint barriers,
remove barriers, move the origin, run or pause simulation, adjust tube-growth
reinforcement and erosion, inspect virtual flow and path history, and view
active-tube telemetry. Arrow keys move the grid selection; Enter applies the
chosen brush. It is responsive and honors reduced-motion preferences.

An original, deterministic solver approximates the **flow-conductance**
feedback concept:

```text
Q_ij = (D_ij / L_ij) (p_i - p_j)
D_next = clamp(D + dt [alpha * |Q|/(k + |Q|) - beta*D])
```

Pressure is estimated by relaxed iteration on a graph Laplacian. Active
transport strengthens conductance; unused tubes shrink. A low-resolution
residual trail is a **visual analogy**, not actual Physarum memory or a
validated representation of biochemical oscillation, food-gradient diffusion,
organelle activity, reaction-diffusion kinetics, or physical tube diameter.
Model parameters and displayed flux are **dimensionless**; they are not
experimental predictions.

## Physicalize / get a 180 × 120 mm SVG blueprint

Press **DOWNLOAD PHYSICAL SVG** after running the simulation. The output
contains scale-marked tube paths and food/origin markers, suitable for manual
inspection, printing or import into a vector/CAD package. Verify print
scaling and manufacturability before using it. This exports a visual
**layout concept**, not a fabrication-certified assembly, a viable living
culture, or machine control. The SVG has millimeter dimensions,
no embedded code, and no external URL dependencies.

Alternatively export the full grid as **CL1 graph JSON** (source metadata,
edges, flux, conductance and obstacles) or a Canvas PNG. The downloads are
initiated locally by the user, not uploaded to an account.

## Open and control

```bash
cd ~/xunia-xenology-live && git pull --ff-only && bash scripts/xunia-cosmos
```

Open the printed local server URL with `/physarum/`, for example
`http://127.0.0.1:8873/physarum/`.

Cmd/Ctrl+K focuses a finite **local interface console**:

```text
/food 15 4
/wall 8 6
/step 120
/health
/blueprint
```

Also supported: `/source X Y`, `/erase X Y`,
`/brush food|barrier|erase|origin`, `/play`, `/pause`,
`/reset`, `/export`, and `/capture`.

## Brain / ecosystem integration

The existing GPT-DOUG BrainKernel now loads a small local, source-qualified
Physarum ontology when tasks explicitly mention slime mold, *Physarum*,
plasmodium, Amoebozoa or “The Blob”. The evidence is appended as contextual
facts with URLs and remains subject to the existing brain safety/provider
preflight. It does not train new model weights or connect to living neurons.

This module is linked from XUNIA HQ, CL1 Synapse, Fusion, the Biological Data
Center, and the resource registry. Other subsystems may consume the exported
JSON/SVG explicitly; there is no unattended network rewiring.

## Validation

```bash
node --check docs/physarum/model.js
node --check docs/physarum/forge.js
node tests/xunia_physarum_model_smoke.js
python3 -m unittest discover -s tests -p 'test_xunia_physarum.py' -v
python3 tests/xunia_physarum_chrome_smoke.py
```

The GitHub Actions COSMOS workflow checks the scientific ontology,
read-only brain integration, numerical adaptation, physical design export,
and live Chrome controls (including reduced-motion mode) on Python
3.11 and 3.12.

**Constraints:** No paid APIs, Vercel, cloud neuroscience hardware,
credentials, biological culture or physical actuation. This
is a scientifically grounded **bio-inspired computational analogy**.
