# Cesium Global Awareness Demo

A small static browser app that fixes the gap between the proposed architecture and a runnable Cesium globe.

## Run it
- Open `index.html` in a browser with internet access, or serve this directory with any static web server.
- The page loads CesiumJS from jsDelivr and OpenStreetMap tiles over HTTPS.
- No Cesium Ion token, backend, API key, Vercel, or build step is required.
- If the repository's GitHub Pages site is enabled, this directory can be published as the root static site.

## Scope
Read-only geospatial visualization with fictional illustrative event records. It has no live feeds, person tracking, targeting, engagement, or external actions. It is not for operational or emergency decisions.

## Troubleshooting
If the globe stays blank, check whether the browser/network blocks `cdn.jsdelivr.net` or `tile.openstreetmap.org`. A visible in-page error appears if the CesiumJS library fails to load.
