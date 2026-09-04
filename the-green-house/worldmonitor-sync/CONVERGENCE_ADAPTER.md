# WorldMonitor Convergence Adapter

The Green House exposes a local Black House compatibility endpoint for WorldMonitor geographic convergence:

```text
GET /v1/intelligence/convergence?region=MENA&time_window=6h
```

## Why this is an adapter

WorldMonitor documents geographic convergence as the MCP tool `get_signal_convergence`, not as a direct REST endpoint. The upstream tool analyzes one-degree grid cells where multiple signal domains co-occur. The current upstream convergence feeds are protests, military flights, naval vessels, and earthquakes, and the upstream convergence engine uses a fixed 24-hour event window.

The adapter therefore does **not** claim that `https://api.worldmonitor.app/v1/intelligence/convergence` is an upstream route. It translates the Black House compatibility request into an authenticated MCP `tools/call` request, then normalizes the result.

## Authentication

WorldMonitor's documented server-to-server API-key header is:

```text
X-WorldMonitor-Key: <key>
```

Store the key only in your local/server environment:

```bash
export WORLDMONITOR_API_KEY='wm_...'
```

Do not commit the key. The adapter also accepts `WM_API_KEY` as a local compatibility alias. A `wm_...` API key is never sent as an OAuth bearer token.

## Run as a local gateway

From the repository root:

```bash
python3 the-green-house/bin/worldmonitor-convergence.py --serve
```

Then call the Black House compatibility endpoint:

```bash
curl 'http://127.0.0.1:8787/v1/intelligence/convergence?region=MENA&time_window=6h'
```

The server is loopback-only by design.

## Direct CLI query

```bash
python3 the-green-house/bin/worldmonitor-convergence.py \
  --region MENA \
  --time-window 6h \
  --min-domains 3
```

## Response contract

```json
{
  "status": "success",
  "data": [
    {
      "type": "multi_signal_convergence",
      "signals": ["military_flight", "military_vessel", "protest"],
      "confidence": 0.89,
      "confidence_basis": "normalized_from_worldmonitor_convergence_score_0_100",
      "score": 89,
      "total_events": 7,
      "cell_id": "34,35",
      "location": {
        "lat": 34.05,
        "lng": 35.12,
        "name": "Eastern Mediterranean"
      }
    }
  ],
  "meta": {
    "source": "WorldMonitor MCP/get_signal_convergence",
    "requested_region": "MENA",
    "requested_time_window": "6h",
    "source_time_window": "24h",
    "window_exact": false
  }
}
```

`confidence` is a Black House compatibility normalization of WorldMonitor's documented 0-100 convergence `score`; the original score is preserved alongside it.

## Time-window semantics

WorldMonitor's convergence engine uses a fixed 24-hour source window. If the compatibility caller requests `6h`, the adapter **does not pretend** the upstream result is six-hour exact. It returns:

```json
{
  "requested_time_window": "6h",
  "source_time_window": "24h",
  "window_exact": false
}
```

A request for `24h` is marked exact.

## Region semantics

`MENA` is a Black House compatibility alias, not a WorldMonitor-native region taxonomy. Its current bounding box is defined in `the-green-house/config/worldmonitor-regions.json` so the scope is reviewable and change-controlled.

## Security properties

- API key is read from environment only.
- Key is not accepted in query parameters.
- Key is not returned in responses.
- Local gateway binds only to loopback.
- Upstream content is treated as data, not executable instructions.
- No external write/action capability is added; this integration is read-only intelligence retrieval.
