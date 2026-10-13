# GPT-Doug × ATAK-Maps — Documented Ecosystem

**Scope:** offline, civilian geospatial map-source registry with a separate synthetic-only viewer and operator-approved USGS imagery. This is not official ATAK, a TAK Server client, a military field app, or a live device network.

## Sources and attribution

- [sonoxo/ATAK-Maps](https://github.com/sonoxo/ATAK-Maps) (fork of the Joshua Fuller project)
- [MOBAC XML reference](https://github.com/sonoxo/ATAK-Maps/blob/master/docs/xml-reference.md)
- [Creating maps](https://github.com/sonoxo/ATAK-Maps/blob/master/docs/creating-custom-maps.md)
- [ATAK install and offline cache guide](https://github.com/sonoxo/ATAK-Maps/blob/master/docs/install-guide.md)
- [Map XML schema](https://github.com/sonoxo/ATAK-Maps/blob/master/schema/mobac-maps.xsd)
- [Original MIT license](https://github.com/sonoxo/ATAK-Maps/blob/master/LICENSE): Copyright (c) 2023 Joshua Fuller.

Inspected source revision: `9dd45641a6849bf52e56b279e39b27126573c434` (2026-10-13). The repository currently contains 42 XML definitions in provider folders even though its README advertises 40. Dynamic enumeration prevents stale counts.

The repository's license covers its software as licensed; it does not grant Google, Bing, Esri, Ordnance Survey or other proprietary tile/imagery access, rights to cache or redistribution. Each vendor requires separate terms review. Keyed providers remain metadata only.

## Source model

- `customMapSource`: TMS/XYZ or quadkey raster tiles. Requires name/url/maxZoom; supports z/x/y/q/serverpart and optional invertYCoordinate.
- `customWmsMapSource`: Web Map Service URL, layers, tile type, min/maxZoom, styles and EPSG reference. In 1.3.x ATAK uses CRS:84 for WGS84 axis order.
- `customMultiLayerMapSource`: child maps combined with `layersAlpha` and common spatial reference.

`tak_geo/map_sources.py` reads these sources locally, checks bounded XML structure and URLs (not full XSD compliance), and builds an SHA-256 catalog with source revision and access policies. `tak_geo/atlas_ontology.py` generates a graph linking repository, sources, providers, categories, formats, and review policies.

The indexer **never performs HTTP requests, runs source code, embeds keys, or connects to TAK Server**. Live external sources cannot be inferred from XML definitions.

## Install / launch in an existing GPT-Doug repository

After switching to the reviewed ecosystem feature branch:

```bash
cd `/Downloads/gpt-doug-warfighter
git clone https://github.com/sonoxo/ATAK-Maps.git ../ATAK-Maps
bash scripts/doug-max tak-geo maps-doctor --source ../ATAK-Maps
bash scripts/doug-max tak-geo ecosystem --source ../ATAK-Maps --output build/tak-maps-ecosystem
open build/tak-maps-ecosystem/atlas.html
```

Skip `git clone` if `../ATAK-Maps` already exists as a checkout. The resulting folder includes:
- `atlas.html`: provider/category/format graph and searchable catalog
- `index.html`: local CoT/GeoJSON geospatial viewer and synthetic observation exercise
- `catalog.json`: sanitized, versioned source metadata
- `atlas-ontology.json`: machine-readable documentation graph
- `ecosystem-status.json`: accurate connection status and review counters
- `data.geojson` / `manifest.json`: synthetic viewer data and offline posture

The browser does **not** request tiles from arbitrary catalog providers. USGS topographic/aerial imagery is separately available only after operator opt-in in the existing map viewer, and its tile requests disclose the viewed map area.

## Versioned audit

To reproduce the inspected source revision in a **fresh, disposable** ATAK-Maps clone:

```bash
git clone https://github.com/sonoxo/ATAK-Maps.git `/Downloads/ATAK-Maps-audit
git -C `/Downloads/ATAK-Maps-audit checkout --detach 9dd45641a6849bf52e56b279e39b27126573c434
cd `/Downloads/gpt-doug-warfighter
bash scripts/doug-max tak-geo maps-doctor --source ../ATAK-Maps-audit
```

This does not modify the developer's existing `ATAK-Maps` working tree.

## Review and security policy

- Bounded 128 KB-per-XML, 256 XML overall. Never process DTD/ENTITY, symlinks, local/non-global IP URLs, embedded credentials, or non-HTTP(S) endpoints.
- TMS placeholders, zoom, WMS layers, CRS and composite alpha are checked; this is a **structural profile**, not full XSD validation. Upstream mapvalidator and XSD checks remain authoritative for source-release validation.
- No vendor URLs, map imagery, or secrets are included in generated metadata.
- Source XML must be inspected independently for provider usage rights and current tile availability before external use.
- All real TAK SDK, device, team location or TAK Server integration requires separate authorization, licensing, cyber review, and human approval.
- CI tests exercise fake local XML and a pinned checkout of `sonoxo/ATAK-Maps` without executing that checkout's code.

Run: `python3 -m pytest -q tests/test_atak_maps_ecosystem.py tests/test_tak_geo.py`.
