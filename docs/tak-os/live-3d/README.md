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

## iPhone Cloud Grid — October 2026

The public Live Earth workspace is an installable iPhone Safari web application, **not** a native iTAK replacement. Open a separately deployed HTTPS page in Safari and use **Share > Add to Home Screen**; the route-specific manifest launches the **real-source** Live Earth interface, never the synthetic training simulator.

- Full-screen touch globe with **MAP**, **LAYERS**, **ONTOLOGY** and **GRID** controls, iOS safe-area insets, landscape view and accessible control labels.
- iPhone Cesium profile bounds GPU resolution, globe tile cache and geometry error. Civil satellite SGP4 redraws less frequently, and USGS/NASA loading begins before secondary providers.
- The WGS84 30-degree coordinate grid is a **reference overlay**, not telemetry, a sensor-coverage estimate or inferred threat zone.
- Cloud badge shows actual **USGS/NASA/NOAA/CelesTrak source health (0-4)**. On-demand OSM buildings are not counted as a live connected source; failures never promote missing data.
- The service worker stores only same-origin UI code for shell recovery, **not** external provider responses, Cesium CDN assets, tokens, private CoT, or TAK Server data. Offline shell access **is not** offline live telemetry.
- Read-only public APIs are fetched directly by each active browser. There is **no centralized persistent collector** or guaranteed 24/7 relay.

**iTAK interoperability:** Apple iOS uses official **iTAK**, whereas ATAK-CIV is Android-only. A real iTAK-to-TAK-Server connection requires an owned/authorized deployment, separate identities and client certificate enrollment, TLS, applicable organizational policy and approval. This public web page holds no TAK credentials and never claims to have joined a TAK Server. Authorized operational layers should never be published into this public source-data map.

### iPhone validation

`node --test tests/test_tak_os_live3d.js` and `python3 -m unittest discover -s tests -p 'test_tak_os_live3d.py' -v` check the PWA manifest, static-route allowlist, shell-only cache, source-health math, mobile resource limits, and the new controls. Actual Safari WebGL fidelity, live provider availability and iOS Add to Home Screen installation require real-device testing after deployment.

### ATAK-style iPhone scaling (map-first)

The iPhone viewport opens on the real Cesium 3D globe with **no large control drawer covering the map**. MAP closes drawers; LAYERS and DATA open bounded, scrollable bottom sheets with a close button. Three touch-sized floating controls zoom or recenter the map, while the top status and bottom five-button dock respect the device safe areas. Cesium continues handling touch/pinch gestures.

The mobile initial camera now frames **North America**, not an overly distant full-Earth sphere or the user's private device location. An optional, user-triggered **STREETS** layer requests OpenStreetMap raster tiles. The selected preset city (Richmond, Virginia by default) is shown when streets are enabled; camera coordinates are explicitly camera position, never the device GPS location. NASA historical imagery is restored when streets are disabled. OSM contributor attribution and tile request errors are visible. Tiles are not locally cached by the service worker; see the [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/).

Before production acceptance, confirm on physical iPhones in portrait, landscape, Safari with its bars expanded/collapsed, and standalone Add to Home Screen. Automated route and JavaScript tests cannot replace physical Safari WebGL testing.


## Private iTAK / TAK Server metrics (opt-in)

The iPhone DATA inspector attempts a same-origin `/tak-os/api/v1/itak/capabilities` request. **GitHub Pages is static** and cannot serve this private API; public xunia.org shows disconnected/unavailable, not fabricated counts. The local Python gateway implements a protected, **read-only, admin-authenticated** TAK Server aggregate metrics connector. The source is official `GET /actuator/custom-network-metrics`; there is no iTAK-specific count exposed by this aggregate endpoint.

Set these only on the **private server**, never in HTML, GitHub Pages, client JS, screenshots, or committed `.env`: `TAK_METRICS_BASE_URL=https://owned-tak-server:8443`, `TAK_METRICS_CLIENT_CERT`, `TAK_METRICS_CLIENT_KEY`, `TAK_METRICS_CA_CERT` (files readable only to gateway), and a separate randomly generated `TAK_METRICS_VIEW_TOKEN` of 32–256 characters. Configure authenticated private access/transport between the iPhone and the private gateway; do not expose the local simulator directly to the Internet. The bearer token gives access to server-wide metrics, so restrict it and keep it out of browser persistence. The upstream server certificate is checked against the supplied CA and mutual TLS certs; redirects are rejected. Network counters have source timestamps, nullable derived rates, an all-TAK scope and no identity, geolocation, UID, or CoT payloads. Errors return **unavailable** rather than stale data.

The public page is **not a native iTAK client** and **does not have any TAK Server permission or client certificates**. Actual iTAK-only, location, video, message, or battery telemetry would need separate, documented, permissioned evidence and policy review. Unit test: `python3 -m unittest discover -s tests -p 'test_tak_os_itak_metrics.py' -v`.

### Native iTAK vs private TAK Server metrics on iPhone

The iPhone dock now has a dedicated **iTAK** panel, separate from the public Earth map DATA tab. Public xunia.org remains a static GitHub Pages site and can show the interface but **cannot** access a private TAK gateway by itself. Without an owned TAK Server, authorized certificates and a private gateway session, every live metric remains explicitly NOT CONNECTED or UNAVAILABLE.

An authorized operator can run the Python gateway on a protected host with the TAK_METRICS_BASE_URL, TAK_METRICS_CLIENT_CERT, TAK_METRICS_CLIENT_KEY, TAK_METRICS_CA_CERT, and TAK_METRICS_VIEW_TOKEN environment variables configured only on that host. The iPhone browser needs an authenticated HTTPS route to this same-origin private gateway; the public GitHub Pages origin cannot be used as a relay. Never paste certificate files or credentials into source code or this public repo.

The operator explicitly submits a viewer token from the private page. The browser keeps it only in volatile memory and polls verified counters at ten-second intervals. STOP clears the token and all displayed totals. Backgrounding the app or leaving the iTAK panel also ends polling. Counter resets and transport failures never return stale measurements as current. If the private gateway reuses a recent report, sampleAgeSeconds reflects the true monotonic elapsed time rather than zero.

Displayed counters are **all connected TAK client types**, not iTAK-only devices. Native iTAK client identities, CoT positions, GPS, message bodies, video, and device-battery metrics are not ingested.

## Live public ontology and date telemetry (Oct 2026)

The public Live Earth iPhone DATA panel contains a **Live Source Ontology** reporting provider state, current record count, retrieval timestamp, last provider observation time, and on-demand status. The source taxonomy is preserved in JSON-LD with explicit PROV/source identity edges. Public source summaries are exportable. Never interpret a successfully retrieved old provider observation as a real-time measurement. The UTC and device-local dates displayed in the HUD are current **browser clock time** and do not attest that any provider feed or private TAK Server is connected.

A separate in-memory private ontology projection validates source-scoped mTLS-confirmed TAK Server aggregate measurements, evaluates sample freshness and exposes only the five allowlisted counters. It does not enter public exports, IndexedDB or service-worker caches. An unverified, future, malformed or stale private reading causes the private metrics display to fail closed. No iTAK-specific connection or military operational feed is inferred.
