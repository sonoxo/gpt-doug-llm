# GPT-Doug TAK-GEO Atlas — local geospatial graph and imagery

This is **an independently developed, civilian research viewer**, not ATAK, iTAK, WinTAK, WebTAK, an official TAK plugin, or a connection to a TAK Server. It uses public data-format conventions for local interoperability. It does not package the ATAK SDK or TAK Server binaries and does not use restricted TAK-MIL software.

## Quick start from the existing GPT-Doug repository

Update to the review branch, then run from the repo root:

```bash
bash scripts/doug-max tak-geo status
bash scripts/doug-max tak-geo demo --output build/tak-geo-demo
open build/tak-geo-demo/index.html
```

Or bypass the GPT-Doug shell:

```bash
python3 -m tak_geo status
python3 -m tak_geo demo --output build/tak-geo-demo
open build/tak-geo-demo/index.html
```

## Features

- Offline grid map and interactive drag-pan, zoom, WGS84 coordinate display
- Point markers, polylines and polygons from the included **SYNTHETIC** exercise file
- Alternate **data graph** view showing observation/category membership (not device links)
- Local drag-and-drop/file-picker GeoJSON (`.geojson`/`.json`) or one-event CoT (`.cot`/`.xml`)
- Local GeoJSON export, source/provenance labels, basic metadata inspector, layer toggles and text filter
- Optional USGS The National Map **topography** or **aerial imagery**. Network requests occur **only when explicitly selected**, and contain the viewed map area (tiles), not imported CoT records. Use imagery only for locations you're permitted to disclose via viewport requests.

## Ingest/export from the terminal

```bash
python3 -m tak_geo convert examples/tak_geo/sample-event.cot --output build/sample-event.geojson
python3 -m tak_geo render build/sample-event.geojson --output build/sample-event-view
open build/sample-event-view/index.html
python3 -m pytest tests/test_tak_geo.py -q
```

The importer accepts `FeatureCollection` or `Feature` GeoJSON with Point, LineString or Polygon geometry, and single-event XML CoT with a WGS84 point. Inputs are capped at **2 MB**, **250 features**, and **10,000 coordinate vertices**. `DOCTYPE`/`ENTITY` XML constructs are rejected. Properties are reduced to safe display labels and provenance fields. Invalid/unsupported geometry fails closed.

## Data handling and authorizations

- Local data remains in the browser tab and generated local files; no push or socket to TAK servers.
- USGS map tiles are not preloaded. Opting in to USGS topo/imagery contacts `basemap.nationalmap.gov` for visible tiles. The app does not transfer imported features with tile requests.
- CoT UID, callsign and coordinates can be sensitive. Only import data you have permission to handle and do not publish generated `data.geojson` or `index.html` when it contains private data.
- Rendering does not verify a CoT source, classify entities, infer identities, prove a live position, or offer tactical/targeting, operator-control, or route safety assurances.
- We do not provision, download, or rehost restricted software or bypass tak.gov onboarding. Operational TAK use requires appropriate approval/ATO, permissions, and SDK license review.

## Official references

- TAK homepage: https://tak.gov/
- TAK product and SDK policies: https://tak.gov/pages/our-process
- Official FAQ: https://tak.gov/faq
- Public ATAK-CIV source: https://github.com/TAK-Product-Center/atak-civ
- Published TAK CoT protocol notes: https://github.com/TAK-Product-Center/atak-civ/blob/main/takproto/README.txt
- USGS topographic tiles: https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer
- USGS imagery: https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer
- USGS map-data use terms: https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map

## Scope of this release

**Research-only visualization.** Not real-time situational awareness, not validated terrain planning, not geoposition tracking, not a military app, not field-certified. Future authenticated TAK interoperability must be implemented as a separate, reviewed, explicitly authorized connector; never infer or claim server credentials based on a local viewer.
