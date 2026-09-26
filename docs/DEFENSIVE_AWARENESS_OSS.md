# ZYRA / XUNIA Defensive Awareness OSS Stack

> Governed by the Black House / GPT-DOUG-LLM control plane. This layer is for authorized defensive situational awareness, telemetry, mapping, tracking analytics, resilience, and operator decision support.

## Live upstream status

[![Open MCT](https://img.shields.io/github/last-commit/nasa/openmct?label=Open%20MCT)](https://github.com/nasa/openmct)
[![Cesium](https://img.shields.io/github/last-commit/CesiumGS/cesium?label=CesiumJS)](https://github.com/CesiumGS/cesium)
[![Stone Soup](https://img.shields.io/github/last-commit/dstl/Stone-Soup?label=Stone%20Soup)](https://github.com/dstl/Stone-Soup)
[![Tracktable](https://img.shields.io/github/last-commit/sandialabs/tracktable?label=Tracktable)](https://github.com/sandialabs/tracktable)
[![PostGIS](https://img.shields.io/github/last-commit/postgis/postgis?label=PostGIS)](https://github.com/postgis/postgis)
[![MapLibre](https://img.shields.io/github/last-commit/maplibre/maplibre-gl-js?label=MapLibre)](https://github.com/maplibre/maplibre-gl-js)

These badges update from GitHub automatically, so the integration page reflects upstream activity without manually editing timestamps.

## Architecture

```text
AUTHORIZED LIVE / HISTORICAL TELEMETRY
                 |
                 v
        NORMALIZATION + PROVENANCE
                 |
        +--------+---------+
        |                  |
        v                  v
   STONE SOUP          TRACKTABLE
 track/state fusion   movement analytics
        |                  |
        +--------+---------+
                 v
              POSTGIS
      spatial + temporal store
                 |
                 v
       GPT-DOUG / MAVEN ONTOLOGY
 provenance + policy + confidence
                 |
        +--------+---------+
        |        |         |
        v        v         v
    OPEN MCT   CESIUM   MAPLIBRE
   telemetry    3D        2D
        \        |        /
         \       |       /
          v      v      v
             ZYRA OPERATOR
     alerts + review + evidence
```

## Component roles

| Component | ZYRA / XUNIA role | Default authority |
| --- | --- | --- |
| [NASA Open MCT](https://github.com/nasa/openmct) | live/historical telemetry dashboards and playback | read-only |
| [CesiumJS](https://github.com/CesiumGS/cesium) | 3D globe, terrain, geospatial visualization | visualization only |
| [Stone Soup](https://github.com/dstl/Stone-Soup) | multi-source track fusion and state-estimation research | decision support only |
| [Tracktable](https://github.com/sandialabs/tracktable) | movement/trajectory analytics and anomaly detection | decision support only |
| [PostGIS](https://github.com/postgis/postgis) | spatial storage, safety geofences, historical track store | application scoped |
| [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) | 2D operational map and alert layers | visualization only |

Machine-readable registry: [`safety-shield/integrations/defensive-awareness-oss.json`](../safety-shield/integrations/defensive-awareness-oss.json)

## Data contract

The stack may process authorized live telemetry and real-world coordinates for situational awareness, sensor health, anomaly detection, safety-zone monitoring, incident correlation, and historical playback. Every ingest path should preserve source/provenance metadata and confidence.

Material external actions remain denied by default and require an explicit governed adapter plus human authority.

## Hard boundary

This integration does **not** provide weapon targeting, aimpoint generation, intercept guidance, fire-control cueing, autonomous engagement, or weapons release. Those capabilities are deliberately absent from the registry and must not be inferred from the presence of tracking or geospatial libraries.

The simulation-only ballistic-warning component remains a separate module with stricter input controls.
