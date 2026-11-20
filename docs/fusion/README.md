# CL1 FUSION / NASA + Cloud Fabric + Observation Lab + Typed Ontology

A free, non-kinetic, original **multi-domain visual intelligence atlas** in XUNIA COSMOS.

**Public URL after deployment:** https://xunia.org/fusion/

The visualization reuses the public NASA/JPL eight-planet catalog from `../cosmos/planets/catalog.json` and displays it alongside three **separately labeled local models**: AWS-style cloud architecture, Anduril-inspired human-facing observational panels, and a Palantir-style typed semantic ontology. The page neither resembles an authorized AWS console nor represents an Anduril Lattice or Palantir Foundry product.

## Domains and evidence

| Domain | Objects | Evidence boundary |
| --- | --- | --- |
| NASA/JPL planets | 8 | NASA planetary physical fact values and JPL Table 1 approximate orbital elements (source-backed, 1800–2050); Earth–Moon barycenter proxy |
| Cloud fabric | 7 | **Proposed** vendor-neutral delivery, storage, index, compute, governance and observability components; AWS **diagramming principles only** |
| Operations observation | 7 | **Synthetic** sample tracks, sample sensors, operator console, human review and audit context; no Lattice system, real tracking, radio, weapons or live sensors |
| Semantic ontology | 7 | **Local object-type schema** inspired by publicly documented Foundry ontology concepts; no Foundry/AIP connection |

Total: **29 objects**, **43 typed relationships** (27 versioned core links plus 16 generated NASA planetary instance/provenance links).

The local source asset `ontology.json` declares object types, relation types, evidence states and primary-source links. It is intentionally editable and version-controlled. The NASA `planets/catalog.json` records remain independent and immutable; no redundant planetary values were invented.

## Controls

- **FUSION GRAPH** — all four layers and cross-domain semantic links, with links between NASA records and ontology object/source types.
- **NASA ORBITS** — project Earth and seven other planets using JPL approximate Kepler elements. Date selector bounded to **1800–2050**, optional calendar playback. Onscreen distances are compressed for legibility, not a scale-accurate or precision ephemeris.
- **CLOUD FABRIC** — proposed architecture boundary, cloud nodes and ontology schema relationships; no AWS resources are provisioned.
- **OBSERVATION GRID** — synthetic sample tracks and example sensors, with human review. No airspace claims, device commands or autonomous tasking.
- Search, domain filters, inspect node properties and provenance, select linked objects, pan/rotate and zoom with pointer and keyboard, trace selected object lineage.
- Export the **visible** object+link graph to local JSON, or save actual Canvas screenshot PNG. `RUN LOCAL SELF-TEST` checks catalog, references and visual rendering.
- **Cmd/Ctrl+K** focuses the finite browser command parser. Examples: `/find Earth`, `/select ops-track-a`, `/view operations`, `/date 2030-01-01`, `/trace`, `/capture`, `/export`, `/health`, `/reset`. No command is executed in a shell.
- Honors reduced-motion preferences. No paid APIs, vendor accounts, runtime tracking, autoplay audio, device control or telemetry access.

## Official public references

- NASA Planetary Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/
- NASA/JPL approximate positions: https://ssd.jpl.nasa.gov/planets/approx_pos.html
- NASA public API directory: https://api.nasa.gov/
- AWS Architecture Icons and diagramming guide: https://aws.amazon.com/architecture/icons/
- Anduril public command-and-control overview: https://www.anduril.com/lattice/command-and-control
- Palantir Foundry Ontology concepts: https://www.palantir.com/docs/foundry/ontologies/ontologies-overview

Names identify sources and design inspiration; **no partnership, endorsement, membership, credentials or integration** is implied. No AWS, Anduril or Palantir protected assets, UI source code, branded artwork or official service icons are copied.

**API policy:** NASA/JPL SSD warns against embedding its API directly in browser websites. This site fetches only **its own versioned static files**. Future NASA/JPL or other public-source imports must follow source policy and use opt-in, bounded server-side/local imports with provenance and version checks, not unverified live feed claims.

## Run locally on Mac

```bash
cd ~/xunia-xenology-live
git pull --ff-only
bash scripts/xunia-cosmos
```

The launcher selects the next free localhost port and prints the page URL. Open `http://127.0.0.1:<printed-port>/fusion/` (for example, `http://127.0.0.1:8873/fusion/` when running on 8873).

## Validate

```bash
node --check docs/fusion/fusion.js
python3 -m unittest discover -s tests -p 'test_xunia_fusion.py' -v
python3 tests/xunia_fusion_chrome_smoke.py
```

GitHub Actions runs these checks on Python 3.11/3.12 and in actual Chromium alongside existing COSMOS, Planetary Forge, Xenology and CL1 tests.

## What it is not

This is **not a replacement for NASA Eyes, AWS Console, Anduril Lattice, or Palantir Foundry**. It is a sovereign, browser-only visual model that records sources, makes object-type and link-type relationships explicit, and lets users inspect proposed architectural designs without connecting to restricted or physical systems.
