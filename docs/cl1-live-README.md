# XUNIA HQ / CL1 Living Core

The **CL1 Living Core** is a free, immersive, local-only interactive organism embedded directly into XUNIA headquarters (`docs/index.html`). It connects **eight existing, real public routes** via a spatial canvas and an accessible HTML button panel.

## Controls

- Select any of the eight portal buttons or click a node in the canvas, then use **ENTER** to open its real route.
- **Drag** the 2D-projected spatial model to rotate the camera; **scroll** or use +/− to zoom; **recenter** to restore the original camera.
- On the focused canvas, **Arrow keys** select portals, **Enter** navigates, and **Space** pauses/resumes.
- Switch between **ONTOLOGY**, **SHAGGOTH** and **SIGNAL** for different visualizations of the same connected topology.
- Change **ENERGY** to alter only illustration amplitude and intensity.
- **PAUSE MOTION** and **FULLSCREEN** control the view.
- **SAVE VISUAL PNG** exports the actual current canvas.
- Optional **SOUND ON** creates an original, low-volume synthesized ambient drone using the Web Audio API. Audio never auto-plays, no music is embedded, and sound turns off when leaving the page. If Web Audio is blocked, the page continues silently.
- Browsers with reduced-motion settings default to a still, interactive scene; no audio is enabled automatically.

## Provenance and safety

CL1's silver-liquid organism, orbit markers, Shaggoth, energy slider, and signals are **artistic simulations**, not true biological tissue, astrophysical data, extraterrestrial contact, physics simulation, hardware actuation, surveillance, radio transmission or a sensor stream.

All eight destinations are versioned relative links to public pages in this repository: COSMOS, Xenology, Planetary Forge, Biological Data Center, Glass Onion, XUNIA World, Ecosystem Observatory and Cinema OS.

No external JavaScript library, paid API, tracking request, Vercel service, secret, microphone, webcam, device API, or backend is necessary. The view contains no fetched telemetry. Motion is driven by `requestAnimationFrame` and respects visibility and reduced-motion preferences. `<canvas>` keyboard controls are supplemented with ordinary HTML buttons for accessible interaction.

## Run locally

```bash
cd ~/xunia-xenology-live
git pull --ff-only
bash scripts/xunia-cosmos
```

The launcher prints the selected localhost port. Open the **XUNIA HQ** root address on that port (e.g., `http://127.0.0.1:8873/`). Your existing Xenology, Planetary Forge and COSMOS URLs remain available.

## Test

```bash
node --check docs/cl1-live.js
python3 -m unittest discover -s tests -p 'test_xunia_live_core.py' -v
python3 tests/xunia_live_core_chrome_smoke.py
```

The Chromium smoke tests cover real canvas rendering, eight buttons/URL mappings, Shaggoth and Signal modes, energy and camera interactions, PNG serialization, keyboard accessibility, and reduced-motion startup. They are also integrated into the COSMOS GitHub Actions workflow.
