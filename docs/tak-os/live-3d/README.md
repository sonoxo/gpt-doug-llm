# GPT-Doug Live Earth 3D — real public observations, typed ontology

**Independent civilian Earth-observation research interface**, not TAK Product Center software. This is not a tracking, weapon, or intelligence cueing system. No fabricated observations, sample incidents, imaginary orbital positions, or invented building heights are inserted into this production workspace.

## Launch for free

When the feature branch is available, from the repository:

```sh
cd docs/tak-os
sh start.sh real-3d
```

Open the printed localhost address (default **`http://127.0.0.1:8080`**). This serves **only the real public-data workspace**, with no synthetic gateway or training agents. The integrated training gateway also exposes `/live-3d/` under the same host if started separately using `sh start.sh web`.

GitHub Pages version is exposed as `https://xunia.org/tak-os/live-3d/` **only after** merged and Pages deployment succeeds. Public access requires Internet and WebGL. No Cesium ion token, commercial imagery subscription, npm runtime, or paid API is required.

The legacy browser CoT simulator remains a separate **training workspace** at `/tak-os/`. Live Earth 3D never imports those synthetic units or data streams.

## Real 3D visualization

- **CesiumJS 1.145** pinned CDN WebGL Earth; WGS84 ellipsoid for shape. This is a three-dimensional globe, **not** an elevation/photogrammetric terrain model. Without WebGL/CDN access, the interface states that Cesium is unavailable rather than substituting a fake globe.
- **NASA GIBS Blue Marble Next Generation** historical-composite raster base imagery; it is not current orbital video or a live camera. Dated near-real-time MODIS Terra imagery is an opt-in WMS overlay, with explicit requested date and no claim that coverage was available.
- **NASA EONET v3** open natural hazard events, including point/polygon geometry and source observation dates. A polygon centroid is calculated only for the readable label, marked as derived. Poll about every 10 minutes.
- **USGS** earthquake GeoJSON, report time/depth/magnitude, and original source link. Poll about every 2 minutes; map point uses surface-projected longitude/latitude rather than inventing depth geometry.
- **NOAA SWPC** planetary Kp indexed observations. Kp is shown as a **global index in the dashboard**, not placed at fictional local coordinates. Poll about every 5 minutes.
- **CelesTrak** public OMM data for civilian stations/NOAA meteorological spacecraft only. Optional satellite.js **SGP4** propagation estimates 3D positions when fresh element sets are available. Those positions are **model calculations**, not realtime satellite telemetry, sensors, or verified precise tracks. Feed poll about every 45 minutes; recalculation at up to 12-second intervals while the browser tab is active. No classified or military-catalog layer.
- **OpenStreetMap Overpass** on-demand 3D building footprints. Height extrusion occurs **only** where the OSM `height` tag exists and parses to metres/feet within range. Other footprints stay flat. User-triggered requests at least 60 seconds apart, bounded to a small city area and 420 buildings. Attribution is required.

## Typed knowledge graph with real provenance

Observations have a schema with stable source IDs, entity type, reported observation time, ingestion time, original reference URL, geometry or null, methodology, accuracy notes, and provider freshness. JSON-LD export uses PROV-O-like `wasDerivedFrom` edges from observations to source entities. No source is silently promoted to authoritative truth: timestamps, event status, and source age remain visible.

Snapshots are archived **locally in IndexedDB** (best effort) and restored as **historical records only**, never counted as live after restart. A successful fresh provider fetch is required before current data reappears in the globe. If a source errors, its current map markers are removed; archived ontology records retain source lineage, and provider status becomes `FAILED`. No fake fallback markers or synthetic geometry are introduced.

## Truth and uptime boundaries

**There is no such thing as unrestricted "all live data at all times" from public web APIs.** NASA imagery is dated; provider feeds update at different cadences and may be delayed, region-limited, censored by conditions, rate-limited or offline. Browser timers may be throttled when the tab is hidden or laptop sleeps, and public GitHub Pages cannot provide background ingestion by itself. A powered self-hosted collector would be needed for true 24/7 background collection, with proper per-source terms and status monitoring. This release provides browser-active polling and honest source/freshness visibility, not a false 24/7 SLA.

## Privacy and security

- Local CoT gateway still listens only on loopback by default; no remote TAK endpoint and no new privileged write API.
- New WebGL route has a **route-scoped** Content Security Policy granting read-only CDN/imagery/provider requests, while existing CoT pages retain their stricter CSP.
- Network destinations are fixed in source code to allowlisted providers; user input cannot inject a URL. All source text is rendered with `textContent` or canonical source URL validation.
- Record count, downloaded JSON, Overpass area, orbit set age, provider polling frequency and browser memory are bounded. No secrets or tokens are saved.
- Services cited and their usage/terms must remain credited. Overpass and NASA imagery are rate-limited public services, not unlimited data grants.

## Tests

From repository root:

```sh
node --test tests/test_tak_os_live3d.js
python3 -m unittest discover -s tests -p 'test_tak_os_live3d.py' -v
```

These test only local code and local gateway. They include **synthetic fixtures inside test files solely for parser verification**; no test fixtures ship as real observations. Actual public-provider availability must be validated in a network-capable browser after deployment, and live data may be unavailable for network, CORS, policy or provider reasons.

## Sources and credits

- [CesiumJS](https://cesium.com/platform/cesiumjs/) — Apache 2.0
- [NASA GIBS API](https://nasa-gibs.github.io/gibs-api-docs/) — imagery access
- [NASA EONET v3 API](https://eonet.gsfc.nasa.gov/docs/v3)
- [USGS GeoJSON feeds](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
- [NOAA SWPC data](https://services.swpc.noaa.gov/json/)
- [CelesTrak GP data](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [satellite.js](https://github.com/shashwatak/satellite-js) — MIT, SGP4/SDP4
- [OpenStreetMap](https://www.openstreetmap.org/copyright) and [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
