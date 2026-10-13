# NASA / Satellites — free, sourced civil-science layer

Status: **interactive code implemented**; a user must choose to load official feeds. No remote source values are manufactured, and data gaps show as unavailable. No NASA API key is required for these three selected public services. Operational TAK Server connectivity remains OFFLINE.

## Source layers and endpoints

| Layer | Use | Reference | Freshness rules |
|---|---|---|---|
| NASA GIBS WMTS | Dated VIIRS Suomi-NPP / NOAA-20 and MODIS Terra Earth imagery overlay on WebMercator map | https://www.earthdata.nasa.gov/data/tools/worldview and https://github.com/nasa-gibs/gibs-web-examples | User chooses observation day (UTC). Never described as live video. Public imagery zoom supported 2–9; unavailable tile remains blank. |
| NASA EONET v3 | Publicly reported recent natural hazard points | https://eonet.gsfc.nasa.gov/docs/v3 | Opt-in GET `https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=40&days=30`. Only supplied point coordinates, no polygon centroid inference. Report timestamp separate from fetch timestamp. |
| NOAA SWPC | Latest published planetary geomagnetic Kp reading | https://www.spaceweather.gov/products/planetary-k-index | Opt-in GET `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json`. Kp is not a spacecraft location; readings show official observation time. |
| NASA Science | United States civilian Earth observation mission catalog | https://science.nasa.gov/earth-science/missions/ | Landsat and Aqua descriptions are sourced mission profiles, not active satellite positions. |
| WMO OSCAR | Public Chinese and Russian civilian weather and Earth-observation mission catalog | https://space.oscar.wmo.int/satellites/view/fy_4c, https://space.oscar.wmo.int/satellites/view/fy_4b, https://space.oscar.wmo.int/satellites/view/meteor_m_n2_4, https://space.oscar.wmo.int/satellites/view/meteor_m_n2_3 | Mission cards describe capabilities only. Status and individual instruments may change: follow linked source. No positions or command frequencies. |

## End-to-end architecture

```text
Human opt-in in NASA dashboard
  ├─ NASA GIBS public XYZ/WMTS imagery (HTTPS directly to the image tiles)
  │    └─ 256-pixel WebMercator imagery layer above the optional OSM basemap
  ├─ NASA EONET public JSON (read-only HTTPS)
  │    └─ bounded parsing → vetted point markers on existing map
  ├─ NOAA SWPC public JSON (read-only HTTPS)
  │    └─ validated Kp with observation/source timestamps
  └─ static NASA / WMO mission reference cards (cached with app shell)

Local CoT simulator and defensive swarm remain independent and offline from these public sources.
```

**User-facing behavior:** Load data only when the user clicks LOAD PUBLIC FEEDS; both requests can be canceled; each request times out after 9 seconds; records are not stored in gateway SQLite and not sent to the CoT or the swarm. Only validated public points are drawn. Current source timestamps are shown and data export records provenance. When offline, mission metadata and the synthetic TAK demo still function. No telemetry from live military satellites, no interception, jamming, tasking, autonomous operations, weapons control, or connections to government networks.

The browser-side sources do not need CORS proxies or credentials. When a provider refuses browser access, the panel shows the source unavailable instead of bypassing provider policy.

**OSM attribution:** https://www.openstreetmap.org/copyright; public tile policy https://operations.osmfoundation.org/policies/tiles/. NASA imagery attribution: NASA GIBS / Earthdata. NOAA observations: NOAA SWPC. These providers do not endorse this independent demonstration.

## Validate

```sh
python3 -m unittest discover -s tests -p 'test_tak_os_nasa.py' -v
python3 -m unittest discover -s tests -p 'test_tak_os_static.py' -v
```

## Civil-space capability comparison

A free public research interface can outperform a closed presentation through reproducible source citations, offline availability, transparent source timestamps, and data usability. Do not claim that these six mission profiles measure the overall US/China/Russia space capabilities; they are a **small, non-exhaustive public metadata sample**.
