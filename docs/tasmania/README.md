# XUNIA / TASMANIAN DEVIL — CESIUM SPATIAL ONTOLOGY V1

**Status:** Working training-only interactive digital twin, ontology and artifact archive. Browser-verified offline mode; CesiumJS globe integration authored but **not runtime verified** here because the test environment blocks CDN access. **Nothing has been deployed to xunia.org.**

## Open and see everything immediately (one file)

Double-click **`TASMANIA_ONTOLOGY_OFFLINE.html`**. This single file includes:

- interactive 2.5D isometric ground-robot exercise, using the actual existing `KrakenCore.Mission` simulation engine;
- 22 ontology nodes, 37 typed connections, selectable semantic graph and rover details;
- 4 generated concept-model previews with no asset download;
- bundled archival screenshots and embedded browser demos from Kraken, AEGIS and Drone CTF;
- interactive pause, simulation speed, model selection, route clicking, virtual-depth illustration, event log;
- locally generated full snapshot, ontology JSON and synthetic GeoJSON downloads.

Works offline without a subscription, API key, or installed runtime. When CesiumJS is reachable over an internet connection, the application attempts to use a Cesium globe and its embedded `data:` GLB concept models. Browser testing of that external code path remains **unverified** in this environment.

## Real CesiumJS 3D globe (recommended full project)

This version uses the actual CesiumJS `Viewer`, `Entity.model` and `OpenStreetMapImageryProvider` APIs—not a screenshot masquerading as Cesium. It includes separate five `.glb` files (four simulated ground rovers, one inert exercise beacon). CesiumJS is loaded from the [official Cesium 1.146 distribution](https://cesium.com/learn/cesiumjs-learn/cesiumjs-quickstart/) and uses an explicit OpenStreetMap tile layer so no Cesium ion access token is needed.

On macOS, Windows or Linux, in the folder containing `index.html`, run:

```sh
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000/index.html` in your browser. An internet connection is needed **only for CesiumJS and the OpenStreetMap basemap**. If blocked, the isometric digital twin works locally with the same mission, ontology and interactions.

> The 3D globe is an **ellipsoid** with a **fictional training-grid overlay displayed near Tasmania**. It contains no real surface elevation measurements, geotechnical data, field-located robots, or actual drone telemetry. The abstract original 36×24 exercise grid is the simulation's source of truth; the latitude/longitude anchor is purely a display transform. The original Kraken CoT exporter uses deliberately different artificial coordinates near 0°/0°, not the Tasmania presentation anchor.

Cesium/OpenStreetMap references:

- [CesiumJS CDN quickstart](https://cesium.com/learn/cesiumjs-learn/cesiumjs-quickstart/)
- [CesiumJS Entity/model API](https://cesium.com/learn/cesiumjs-learn/cesiumjs-creating-entities/)
- [OpenStreetMap imagery provider & tile policy](https://cesium.com/learn/cesiumjs/ref-doc/OpenStreetMapImageryProvider.html)

## Contents

| File / folder | Purpose |
|---|---|
| `TASMANIA_ONTOLOGY_OFFLINE.html` | self-contained clickable offline edition (Cesium attempts if CDN accessible) |
| `index.html`, `style.css`, `app.js` | source for real CesiumJS web viewer + fallback |
| `kraken-core.js` | unmodified existing KRAKEN physics/routing/sim engine |
| `ontology-data.js`, `data/ontology.json` | same ontology as JSON and file://-compatible JS data |
| `data/example-exercise.json` | real archived synthetic exercise JSON from previous release |
| `models/*.glb` | generated fictional low-poly 3D assets — no engineering CAD |
| `legacy/*` | the previous Kraken, AEGIS and Drone CTF browser artifacts |
| `previews/*` | screenshots and generated robot model concept renders |
| `museum/*` | XUNIA Museum embed/metadata, **prepared, not published** |
| `tests/*` | JS ontology/unit tests, GLB validation, browser interaction checks |
| `tools/*` | reproducible ontology/model/render/offline builders |

## Readiness / evidence

- PASS: **5/5** Node ontology and recovery tests.
- PASS: all **5 GLB model files** have valid glTF headers; four rover models load through trimesh.
- PASS: desktop/mobile offline browser interactions, four screens, select rover, simulation controls, graph node search, in-browser data exports.
- PASS: self-contained HTML edition boots, shows generated imagery and accesses ontology.
- UNVERIFIED: actual CesiumJS CDN loading, Cesium scene and glTF rendering, because this test environment denies remote requests.
- NOT PRESENT: physical excavator/drill control, GPS devices, TAK server connection, sensor feeds, person tracking, autonomous interception, or military readiness accreditation.

To repeat tests in a development environment with installed Python `playwright`, `trimesh`, a local Chromium binary, and Node 18+:

```sh
node --test tests/test_ontology.js
python3 tests/test_models.py
python3 tests/test_browser.py
python3 tests/test_standalone.py
```

The Playwright test harness uses `about:blank` and inline source injection because this build environment prohibits localhost/file navigation. Browser checks therefore validate the complete **offline** application but do not replace an actual hosted end-to-end Cesium test.

## Publishing

Free static hosting via a repository Pages site can serve the entire folder. Preserve the paths for `models/`, `previews/` and `legacy/`; no backend or paid account is needed. For production map usage, comply with the tile provider's license and traffic policy. The XUNIA Museum entry is present at `museum/museum-entry.json` and the card is ready for manual authorized publication. This package does not upload, publish or modify any remote site.
