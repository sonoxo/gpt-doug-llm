# GPT-DOUG Global Intel Benchmark 2030

**Purpose:** provide a public-source, strategic intelligence-quality layer that measures
whether the feeds driving GPT-DOUG are available, timely, structurally valid, and
traceable.

This benchmark is intentionally different from a geopolitical threat score. It
measures **source fitness**, not the danger posed by a country, person, military unit,
or political actor.

## Public sources in v1

- USGS earthquake GeoJSON
- NASA EONET natural-event API
- NOAA SWPC planetary K-index
- CISA Known Exploited Vulnerabilities catalog
- World Bank Indicators API

## Benchmark dimensions

Each source is scored on a 100-point engineering scale:

| Dimension | Weight |
|---|---:|
| Availability | 30 |
| Schema integrity | 25 |
| Latency | 15 |
| Freshness | 20 |
| Provenance | 10 |

The overall score is the mean source score. The benchmark also reports per-domain
scores and median source latency.

## Domains

- NATURAL_HAZARDS
- ENVIRONMENT
- SPACE_WEATHER
- CYBER_DEFENSE
- STRUCTURAL_CONTEXT

## Safety boundary

The Global Intel layer is for public, strategic situational awareness. It does not
provide:

- real-time military unit locations
- weapon targeting
- strike planning
- payload release
- private-person surveillance
- unauthorized access

Natural-hazard map points from USGS and NASA are displayed because they are public
science and disaster-awareness data.

## API

```text
GET /api/v1/intel/global/sources
GET /api/v1/intel/global/benchmark
GET /global-intel
```

The benchmark is cached in-process for five minutes so public source endpoints are
not queried on every browser refresh.

## Shell

```sh
gpt-doug-global-intel
```

The command prints source availability, score, latency, domain scores, and aggregate
signals.

## Future benchmark tiers

A production evolution can separate the score into:

1. SOURCE — availability, integrity, freshness, provenance.
2. FUSION — normalization success, duplication, corroboration, conflict resolution.
3. MODEL — inference calibration, drift, uncertainty, reproducibility.
4. OPERATOR — alert quality, false-positive rate, time-to-triage.
5. RESILIENCE — source failover, offline cache, recovery, replay.
6. COMPLIANCE — evidence completeness and jurisdiction-specific control coverage.

Every tier should preserve source evidence and human decision authority.
