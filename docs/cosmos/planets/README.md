# XUNIA COSMOS / CL1 Planetary Forge

A **free, non-kinetic planetary digital-twin explorer** inside the public XUNIA COSMOS catalog.

**Public target after merge and GitHub Pages deployment:** https://xunia.org/cosmos/planets/

## What this implements

- Eight source-backed reference planets, Mercury through Neptune, with **NASA** physical measurements (diameter, mass, gravity, temperature, spin, axial tilt and orbital period).
- **JPL approximate heliocentric positions** using time-varying six-element Keplerian fits for **1800–2050**, at any date selected in the interface. Mean anomaly is computed from mean longitude minus longitude of perihelion, Kepler's equation solved by Newton iteration, and orbital-plane coordinates rotated into the ecliptic reference frame.
- Planet selection in a projected, interactive orrery. Drag to change camera azimuth/elevation, scroll to zoom, use dates, play/pause and speed controls. The view uses **logarithmically compressed orbital distances** and **nonphysical planet marker sizes** so all eight worlds remain visible.
- Procedural shaded globes with planet-specific illustrative bands, clouds and colors; drag the globe to rotate it. **These are not NASA surface maps, photographic captures, scientific atmosphere simulations, or scale-accurate 3D models**.
- **CL1 sandbox:** up to four separately managed, virtual planet replicas per browser session. Alter a clone's diameter multiplier, spin multiplier and glow/cloud visualization factor. Reference catalog records stay unchanged. Export a clone's sandbox settings as local JSON. No persistence or network writes.
- A restricted browser command console, Cmd/Ctrl+K to focus. It **does not execute terminal/shell code**.

## Commands

`/planet Earth`, `/planet Mars`, `/clone`, `/select clone-1`, `/delete`,
`/radius 1.25`, `/spin -1`, `/glow 60`, `/date 2030-01-01`,
`/speed 30`, `/zoom 1.5`, `/play`, `/pause`, `/export`, `/reset`, `/help`.

Choose a **reference planet** to inspect original values; a **clone** to edit a hypothetical alternative. The viewport marks clone data as hypothetical. Planet 1–8 keys select reference worlds when not typing in a text field. Left/right arrow keys select objects when the orbital canvas is focused.

## Accuracy and provenance

The immutable `catalog.json` bundles public numeric values from:

1. NASA Goddard Space Flight Center, *Planetary Fact Sheet — Metric*: https://nssdc.gsfc.nasa.gov/planetary/factsheet/
2. NASA/JPL Solar System Dynamics, *Approximate Positions of the Planets*, **Table 1**: https://ssd.jpl.nasa.gov/planets/approx_pos.html

The JPL Table 1 **Earth record is the Earth/Moon barycenter**, so Earth's plotted position is a proxy, not exact Earth-center coordinates. The orbital fits are approximate and valid only within the 1800–2050 interval. A browser date uses UTC in a simplified conversion to centuries relative to J2000, while the source JPL solution is based on ephemeris dynamical time. This is an educational visualization, not astrometric-quality ephemerides, precision pointing, orbital mission planning, or dynamics with perturbations. Gravity and temperatures are displayed source facts, not physically simulated forces.

The procedural appearance of every globe is **illustrative**. Planetary locations are source-based approximations, but UI spacing is **logarithmically compressed**. Clone-specific changes are **nonphysical hypothetical sandbox values**; they never alter the NASA/JPL canonical record or drive physical systems.

## Local Mac launch

Use a separate clone destination that won't overwrite other worktrees:

```bash
git clone --depth 1 https://github.com/sonoxo/gpt-doug-llm.git ~/xunia-planetary-forge
cd ~/xunia-planetary-forge
bash scripts/xunia-cosmos
```

Then visit http://127.0.0.1:8872/cosmos/planets/.

Existing CL1/BIO services use other ports and are not replaced.

## Automated validation

```bash
python3 -m unittest discover -s tests -p 'test_xunia_planet_clones.py' -v
python3 tests/xunia_planets_chrome_smoke.py
node --check docs/cosmos/planets/planets.js
```

The smoke test serves a temporary local copy, opens it in real Chromium/Chrome, and checks 8 rendered nodes, click selection, a Mars clone, virtual diameter and rotation controls, dates, typed command dispatch, persistence across source switching, and clone deletion. No external API or paid service required.

## Containment

- Public GitHub Pages frontend + same-origin immutable catalog JSON only; no Vercel, keys, banking, biosensors or paid APIs.
- No transmitters, actuators, physical effectors, real telemetry, autonomous harvesting, system shell execution or cross-origin runtime requests.
- Maximum four in-memory clones per user session; clones do not publish without separately handling locally exported JSON.
