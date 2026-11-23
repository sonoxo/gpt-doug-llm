# XUNIA GLASS ONION — Cyber Intelligence Research Lab

**Public launch path, after merge and Pages success:** https://xunia.org/darkweb/

An **original**, no-account XUNIA interface with all **21 tool references** shown in the source graphic. Product names identify outside services and are not copies of private code, proprietary data, search indexes, Tor Browser, leak stores, Telegram bots, or vendor trademarks. XUNIA does not claim those backends are connected.

## Working in-browser modules
- Searchable, categorized 21-reference catalog, with honest native/integration/reference/restricted labels.
- Ahmia and OCCRP Aleph public-search launchers, redirecting to the real providers.
- Free HIBP Pwned Passwords range API; SHA-1 computed locally and only the first five hexadecimal hash characters sent over HTTPS. Do not check production passwords on this or other unfamiliar sites.
- Free, source-attributed CISA Known Exploited Vulnerabilities catalog. Fetch failures are explicit.
- Browser-only notes/evidence vault: add, search, import JSON/CSV and export JSON; 500-record cap. Browser localStorage is **not encrypted** and must not be used for restricted information or secrets.
- OpenPGP browser station with ECC key generation, encryption, decryption, cleartext signing and signature verification using pinned OpenPGP.js version 5.11.3 from unpkg. Third-party library availability is necessary; an audited installed client is safer for high-value secrets.
- Verified official-source directory and privacy guidance.

## CLI: bounded authorized crawler
Requires Python 3.10+ and **written authorization or ownership** of the exact HTTPS host.

```sh
python3 scripts/xunia_authorized_crawl.py --base-url https://example.org --allow-host example.org --max-pages 10 --authorized > research.jsonl
```

The crawler is designed to fail closed on localhost/internal/hidden services, IP-literal hosts, non-global DNS, redirects off the exact hostname, oversized responses, and missing or unreadable robots.txt (HTTP 404 is interpreted as no robot rules). Same-origin HTML links only; default 2-second delay; maximum 50 pages. It is a bounded audit prototype, not a Tor crawler. **DNS rebinding at socket-connect time is not completely eliminated by pre-request DNS checks; use only trusted approved hosts and isolated environments.**

## Tests
```sh
node --test tests/xunia_glass_onion.test.mjs
python3 -m py_compile scripts/xunia_authorized_crawl.py
```

GitHub Actions workflow `.github/workflows/glass-onion.yml` executes these on push and pull requests.

## Truth boundary
GitHub Pages hosts static files; it does not operate a Tor relay, search engine, breach-data subscription, onion mirror, or secure evidence server. No credentials, private records, or arbitrary websites should be automatically collected. No external commercial service is portrayed as installed. Feature branch builds are not publicly deployed until merged and the Pages job passes. This exhibit follows XUNIA Museum inclusion and provenance guidelines.

## USA Defense Scope v1 / public defensive readiness

**Launch:** `https://xunia.org/darkweb/#usa-defense`

Glass Onion now includes a **U.S.-focused defensive scope planner**. The
scope is deliberately **public-source, non-invasive and non-operational**:
not a nationwide cybersecurity deployment, not a CISA/DHS/NIST/FBI
partnership, not a scanning service or autonomous incident responder.

Its data contract is `usa-defense-scope.json` and its browser-only UI
is `usa-scope-app.mjs` with validated helpers in `usa-scope.mjs`.

### Coverage, not access

- **16 official critical infrastructure sectors**, as recognized by CISA;
  the user can plan across sectors or select one. This is a taxonomy,
  **not** access to infrastructure operators or their security posture.
- **Six NIST CSF 2.0 functions**: GOVERN, IDENTIFY, PROTECT, DETECT,
  RESPOND, RECOVER; two concrete planning actions for each function.
- **Five contexts**: public/community, authorized owner/operator,
  state/local/tribal/territorial teams, small business/nonprofit, and
  federal planning. No program status, eligibility, security authority or
  classified access is inferred.
- **Local action plan** generation and JSON export. Every step is marked
  `NOT_VERIFIED_OR_PERFORMED`; the output explicitly reports
  **zero verified implementations**.
- **External official links only** for CISA critical-infrastructure sectors,
  CISA KEV, NIST CSF, CISA incident reporting, and FBI IC3. Reports are
  filed only through the real agency sites by the user.

No connected assets are discovered, no network scans, endpoint changes,
blocking, live threat monitoring, credential collection or reports are
initiated by this UI. It does not collect private asset inventories or
case details. Users seeking real protection must separately deploy
owner-approved controls and operational response processes. If a CISA
reference changes, the source is reviewed and updated rather than
substituting an invented live status.

**Verified underlying references:** [CISA critical infrastructure sectors](https://www.cisa.gov/critical-infrastructure-sectors),
[NIST CSF 2.0](https://www.nist.gov/cyberframework),
[CISA known exploited vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog),
[CISA incident reporting](https://www.cisa.gov/report), and
[FBI IC3](https://www.ic3.gov/).

**Verification:**

```sh
node --check docs/darkweb/usa-scope.mjs
node --check docs/darkweb/usa-scope-app.mjs
node --test tests/xunia_usa_defense_scope.test.mjs
cd tests/glass-onion-browser && npm test
```

The existing Glass Onion GitHub Actions workflow verifies the scope,
authorization boundaries, both new local-plan browser journeys, and the
original research tools before deployment.

## Global Observatory / near-real-time world views

**Launch after GitHub Pages deployment:** https://xunia.org/darkweb/global/

Independent, open-source, browser-side world map with a local Natural Earth
1:110m public-domain coastline. No commercial mapping service, subscription,
account sign-in, API tokens, or proprietary provider.

- **USGS** all-earthquakes past-day GeoJSON, with source coordinates.
- **NASA EONET** open-events API, curated natural phenomena. Only events with
  valid point coordinates are plotted; polygons are excluded, not given
  synthetic center points.
- **CISA** Known Exploited Vulnerabilities (KEV) JSON, shown in a **separate
  non-geographic panel**. The catalog provides no attack-location telemetry.
- Source integrity and fetch times appear independently for every feed.
  Failed sources are cleared, not portrayed as having live data.
- Browser-side 5-minute refresh while visible, manual refresh, time/layer/
  magnitude/search filters, accessible event-list selection, drag/pan/zoom,
  provenance links, and local JSON export.
- The geographic view plots up to 450 filtered events for performance;
  the list shows up to 65 events. Counters state the display cap.
  USGS covers 24 hours; NASA open-event observations can be older.
- GitHub Pages does **not** operate a global sensor network, security
  operations center, national defense system, automated remediation
  backend, or active cyberattack monitoring. No targets are scanned.
  No private telemetry, credentials, government permissions or paid APIs.

**Verification:**

```sh
node --test tests/xunia_global_observatory.test.mjs
cd tests/glass-onion-browser && npm test
```

The existing Glass Onion workflow validates the registry, script syntax,
unit cases, browser-mocked failure cases, and static website integration.

## COSMOS EYES / source-qualified space observatory

**Route (after publish):** https://xunia.org/darkweb/cosmos/

Interactive, free, static-site space-weather laboratory with the following
public authoritative feeds:

1. NOAA SWPC real-time solar wind (L1) and magnetic field products.
2. NOAA planetary Kp index and GOES primary X-ray measurements.
3. NOAA OVATION aurora model output on source geographic grid coordinates.
4. A direct link to the official NASA/JPL near-Earth close-approach table; no JPL API is embedded in this website because its terms prohibit it.
5. NASA Solar Dynamics Observatory latest public 193 Å image (provider
   image age not inferred from the browser retrieval time).

Browser refresh: 2 minutes for NOAA while the tab is visible. JPL is external navigation only. NOAA observation
timestamps are checked against distinct freshness limits; errors and stale data
do not present made-up values. Aurora forecast grid points are only rendered
for current source timestamps. NOAA model intensity is not a direct sighting.
Solar wind and Kp charts show only actual measured series (no extrapolation).
CSP permits only the five NOAA public endpoints' host and the SDO image host.
NASA's official Eyes projects are linked for 3-D mission/asteroid simulation.

**Scope:** Public data and delayed science products only; does not relay
spacecraft instrument video, cover the whole cosmos, locate UAPs, monitor
classified systems or imply government access.

```sh
node --test tests/xunia_cosmos_eyes.test.mjs
cd tests/glass-onion-browser && npm test
```

## Non-Kinetic Arsenal / Palantir-style public evidence ontology

**Route after merge and Pages deployment:** https://xunia.org/darkweb/nonkinetic/

An original, locally rendered, free, **read-only public-record model** of
11 named U.S. non-kinetic defense programs, as documented through
November 22, 2026. **Not an exhaustive inventory or an "active arsenal" feed.**

- Capability system objects, service branches, high-level roles/domains,
  public program milestones, and independently linked official evidence.
- Relationship graph supports `CapabilitySystem → ServiceBranch`,
  `CapabilityDomain`, `PublicReadinessState`, and `EvidenceRecord`.
- Branch, category, public milestone and text filters; keyboard-accessible
  graph objects and catalog cards; selection inspector with official source.
- Filtered graph/records export as JSON. No editing of government data.
- Development/test, contract award, installation, fielding, publicly
  reported use and operational acceptance are separate historical statuses.
  **Every record explicitly carries "NOT_PUBLICLY_VERIFIED" current activation
  and "NOT_CONNECTED" telemetry.**
- No equipment location, target data, frequencies, tactical weaknesses,
  inventory quantities, troop movements, live readiness or fleet access.

This is inspired by the *concepts* in the public [Palantir Foundry Ontology
documentation](https://www.palantir.com/docs/foundry/ontology/).
**No Palantir Foundry/AIP/Maven tenant, credentials, government data
subscription, defense network, or physical system is connected.** The
implementation is static JavaScript + a provenance registry, not Palantir.

**Verification:**

```sh
node --test tests/xunia_nonkinetic_ontology.test.mjs
cd tests/glass-onion-browser && npm test
```

Production deployment is gated by the existing Glass Onion GitHub Actions
checks and the XUNIA Museum GitHub Pages publisher.

## SWARM / HIVE / SWEEP — real browser fieldlab (not a picture)

**Public route:** https://xunia.org/darkweb/fieldlab/ (after merge and Pages deployment).

Open-source, self-contained science application; no paid services, no backend or
credentials. This new live model is linked from the Glass Onion home page,
COSMOS EYES, the global observatory, and the public non-kinetic ontology.

### Actual software and source feeds

| Sensor / catalog | Public endpoint | Use |
| --- | --- | --- |
| NOAA L1 plasma | `services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json` | Observed wind speed/density |
| NOAA L1 magnetic | `services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json` | Observed interplanetary Bz |
| NOAA planetary Kp | `services.swpc.noaa.gov/products/noaa-planetary-k-index.json` | Observed geomagnetic index |
| NOAA GOES X-ray | `services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json` | Observed flare class |
| NOAA OVATION | `services.swpc.noaa.gov/json/ovation_aurora_latest.json` | Modeled aurora on source grid |
| USGS global quakes | `earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson` | Time-stamped source events |
| NASA EONET | `eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200` | Public open natural events |

SWARM independently fetches these seven resources at two-minute intervals while
the page is visible, with 18-second timeouts. An unavailable source clears its
measurements. Stale NOAA instruments and old USGS feed generations are not
presented as current. EONET's "open" status is an event catalog, **not**
evidence of a newly observed event today; reported observation timestamps stay
visible. No background daemon or persistent surveillance is created.

### Numerical model and visualization

- **3-D orthographic Earth:** Real Natural Earth public-domain land outlines,
  latitude/longitude projection, drag/touch/wheel/keyboard camera controls,
  UTC solar illumination from a low-precision solar ephemeris, opt-in camera
  orbit, layers for NOAA aurora model cells and source-located USGS/NASA events.
  The globe is a computational canvas, **not an image mockup** or literal
  photographic satellite feed.
- **Proton dynamic pressure** from validated L1 density and speed:
  `P[nPa] = 1.67262192e-6 * density[cm^-3] * speed[km/s]^2`.
  Source: NASA/Aerospace SEAES-FC User's Guide, Appendix E.2
  https://ccmc.gsfc.nasa.gov/seaesfc/ATR-2022-01665.pdf
- **Pressure-only magnetopause proxy:**
  `R[Earth radii] = 10*(2/P[nPa])^(1/6)` by definition normalized to 10
  Earth radii at 2 nPa. A teaching approximation **not** a measured,
  validated real-time magnetopause position or full Shue/MHD model.
- **Nominal L1 propagation estimate:** `1,500,000 km / wind speed` (minutes
  after dividing by 60). It neglects flow path, spacecraft position, storm
  structure and other effects; **not a reliable arrival forecast**.
- **Isolated what-if scenario** sliders vary plasma density and speed, changing
  only the derived model, never altering actual NOAA readings or source status.
- **HIVE** normalizes source frames and retains evidence/provenance, shows event
  inspector, and exports a bounded attributed JSON snapshot.
- **SWEEP** detects explicitly defined thresholds for Kp, negative Bz,
  solar-wind speed, M-class X-rays and recent USGS magnitude ≥5 events. These
  are environmental flags, not military threat predictions, cyberattack
  detection, earthquake forecasts or causal links among the feeds.

### Operational and privacy guardrails

Browser-only, read-only, public-data science. Not Palantir Foundry, not a
government integration, not real-time military activation or an "active
arsenal" tracker. No defense personnel, unit positions, frequencies, commands,
target lists, classified source claims, weapon controls or off-site data uploads.
The restrictive CSP allows only the three listed official agency hosts for
data and the site's static assets. When the canvas is unavailable the public
source readings and validation remain usable.

### Validation

```bash
node --check docs/darkweb/fieldlab/model-core.mjs
node --check docs/darkweb/fieldlab/earth-renderer.mjs
node --check docs/darkweb/fieldlab/fieldlab.mjs
node --test tests/xunia_fieldlab_live_model.test.mjs
cd tests/glass-onion-browser && npm test
```
