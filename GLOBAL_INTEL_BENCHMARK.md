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

## Evidence health update — October 14, 2026

The existing read-only feed benchmark is now paired with a distinct **evidence
quality / provenance graph**. Availability, latency or a good score do **not**
mean that a statement has been independently verified.

### New API and local CLI

```text
GET /api/v1/intel/global/evidence
GET /global-intel
```

The Global Intel dashboard shows a separate evidence-health section for the five
curated public sources. The new API reuses the five-minute cached benchmark, so
it does not multiply upstream requests.

For an offline, human-reviewed benchmark file:

```bash
python3 -m agency_cloud.intel_evidence --input /path/to/benchmark.json   --output build/intel/public-source-evidence.json
```

The CLI does **not** contact remote sources. To replace generated local output,
append `--force`. Never confuse this with Git force push.

### Evidence / ontology contract

```text
Approved official public source
       |
       +--> Parsed source summary (SHA-256 of normalized parser SUMMARY)
                     |
                     +--> Feed fetch status and fetch age
                     +--> Last catalog entry / event timestamp and age
                     +--> SOURCE_STATEMENT_UNCORROBORATED
                     +--> ANALYTIC_CONFIDENCE = NOT_ASSESSED
                     +--> REVIEW_REQUIRED
```

The hash does **not** represent raw upstream feed bytes, digital signatures,
source authenticity, model accuracy, or patent/license ownership. Events in the
feed cannot be asserted as independently corroborated. No raw map coordinates,
private-person data, external actions or tasking are included in the evidence
graph. The existing hazard viewer remains based on public natural-hazard
geometry.

The five source-specific "last entry" clocks mean:

| Source | `observedAt` represents |
| --- | --- |
| USGS | GeoJSON feed metadata-generated timestamp |
| NASA EONET | Date of last geometry point in returned event set |
| NOAA SWPC | Latest reported planetary K-index observation |
| CISA KEV | Most recent vulnerability `dateAdded` (NOT catalog fetch time) |
| World Bank | End of latest non-null indicator reporting year |

A feed retrieved today can contain old observations; an old catalog entry date
does **not** prove the feed is offline. Distinct `fetchState` and `lastEntryState`
flags prevent those cases from being conflated. Future-dated timestamps are
marked rather than treated as fresh. Unknown timestamps never earn full
freshness points.

### Ingestion hardening

- Only predefined approved HTTPS hosts and source IDs are ingested.
- Redirects to unapproved hosts, userinfo or nonstandard ports are rejected.
- Responses are capped at 6 MiB, with an error on oversize data.
- NaN/infinite coordinates and NOAA indices are not promoted to JSON/map data.
- Unrecognized source URLs, mismatched provenance, duplicate sources, malformed
  summaries and nonfinite numbers are rejected or quarantined as summarized
  rejections; untrusted raw content is not echoed to public error reports.
- Unit tests use synthetic fixtures; passing offline CI is not proof of current
  endpoint availability or real-world operational certification.

### Development acceptance

```bash
python3 -m unittest discover -s tests -p 'test_global_intel_evidence.py' -v
```

Existing API `/api/v1/intel/global/benchmark` remains compatible and
continues to evaluate the five curated sources. Real connectivity requires the
deployed service to have outbound HTTPS access. The new route and dashboard
changes do not become live until the reviewed PR is merged and deployed.

## Future benchmark tiers

A production evolution can separate the score into:

1. SOURCE — availability, integrity, freshness, provenance.
2. FUSION — normalization success, duplication, corroboration, conflict resolution.
3. MODEL — inference calibration, drift, uncertainty, reproducibility.
4. OPERATOR — alert quality, false-positive rate, time-to-triage.
5. RESILIENCE — source failover, offline cache, recovery, replay.
6. COMPLIANCE — evidence completeness and jurisdiction-specific control coverage.

Every tier should preserve source evidence and human decision authority.
