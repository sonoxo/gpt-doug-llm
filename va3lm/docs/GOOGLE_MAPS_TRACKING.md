# BIG VIRGINIA // VA3LM Google Maps Tracking

VA3LM 0.3.0 adds an authorization-bounded geospatial tracking surface for assets, vehicles, sensors, sites, and events.

## Public source reference

The architectural reference requested for this update is the NSA public episode:

- **How We Found Bin Laden: The Basics of Foreign Signals Intelligence**
- YouTube: https://www.youtube.com/watch?v=Om-OyjADgTA
- Official NSA page: https://www.nsa.gov/Podcast/View/Article/3895171/how-we-found-bin-laden-the-basics-of-foreign-signals-intelligence/

VA3LM does **not** reproduce interception methods or covert person-tracking techniques. The safe adaptation is limited to high-level analytic workflow principles: preserve provenance, timestamp observations, correlate multiple observations, retain confidence/uncertainty, visualize geospatial context, and require analyst/human review.

## Google Maps technology

The runtime map surface uses the **Google Maps JavaScript API**. The tracking API emits standard GeoJSON-compatible point features that can also feed other map clients.

Optional future integrations can use:

- Routes API / Routes library for authorized route computation
- Geocoding API for address-to-coordinate and reverse-geocoding workflows

Google Maps Platform requires a Google Cloud project, billing, enabled APIs, and an API key.

## Configure

Create a **browser-restricted** Google Maps API key and enable the Maps JavaScript API. Do not commit the key.

```bash
export GOOGLE_MAPS_BROWSER_KEY='YOUR_BROWSER_RESTRICTED_KEY'
cd va3lm
va3lm serve
```

Open:

```text
http://127.0.0.1:8088/tracking-map
```

For deployed web applications, restrict the browser key by the exact HTTP referrers that host the VA3LM map UI. Use a separate server-restricted key if a future server-side Maps API integration requires one.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/tracking` | Tracking capability/source/boundary manifest |
| GET | `/api/tracking/sample` | Deterministic Virginia demo track as GeoJSON |
| POST | `/api/tracking/geojson` | Validate and normalize authorized observations to GeoJSON |
| GET | `/tracking-map` | Google Maps visualization of the deterministic demo track |

## CLI

```bash
va3lm tracking
va3lm tracking --sample
```

## Observation contract

Each point contains:

- non-person `track_id`
- entity type: `asset`, `vehicle`, `sensor`, `site`, or `event`
- label
- latitude / longitude
- UTC-capable timestamp
- source/provenance
- confidence score
- non-identifying metadata

Identity-oriented metadata such as person names, persistent person IDs, phone identifiers, IMEI/IMSI values, or biometric fields is rejected by the core contract.

## Flow

```text
AUTHORIZED SOURCE
      ↓
OBSERVATION + PROVENANCE
      ↓
TIMESTAMP + LAT/LONG + CONFIDENCE
      ↓
TRACK NORMALIZATION
      ↓
GEOJSON
      ↓
GOOGLE MAPS
      ↓
ANALYST REVIEW
      ↓
HUMAN APPROVAL GATE
```

## Status

This feature provides the data contract, API, CLI, deterministic demo, map UI, and tests. It does not create a live GPS feed by itself. A live deployment must connect an explicitly authorized telemetry source and maintain appropriate consent, access control, retention, and audit policy.
