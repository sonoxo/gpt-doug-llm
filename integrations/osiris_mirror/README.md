# GPT-DOUG OSIRIS Safe Mirror

A persistent, read-only mirror for approved **public/non-tactical** OSIRIS layers.
It is designed to keep GPT-DOUG/Cesium aligned with the safe public portions of
OSIRIS while preserving provenance and stale-data status.

## What “mirror GPU” means here

- **Mirror**: continuously refresh JSON from the configured OSIRIS instance.
- **GPU**: Cesium/WebGL renders mirrored data on the operator's own GPU.
- **No parasite behavior**: this code does not hijack, borrow, mine on, or consume
  third-party compute; it does not install stealth persistence or evade controls.

## Mirrored routes

`health`, `earthquakes`, `fires`, `weather`, `air-quality`, `space-weather`,
`news`, `live-news`, `gdelt`, and `markets`.

The worker intentionally blocks tactical/recon routes including live flights,
CCTV, conflicts/frontlines, maritime/radar, scanning/OSINT, infrastructure,
and satellite tracking.

## Run

```bash
export OSIRIS_BASE_URL="http://127.0.0.1:3000"
python3 integrations/osiris_mirror/osiris_mirror.py --once
python3 integrations/osiris_mirror/osiris_mirror.py
```

Snapshots are written to:

```text
~/.local/share/gpt-doug/osiris-mirror/snapshot.json
~/.local/share/gpt-doug/osiris-mirror/status.json
```

For a subset of safe routes:

```bash
export OSIRIS_MIRROR_ROUTES="earthquakes,fires,weather,space-weather,news"
```

## macOS always-on mode

Copy the example plist to `~/Library/LaunchAgents/`, replace `__REPO__` with the
absolute repository path, then load it with `launchctl bootstrap gui/$(id -u)`.
`KeepAlive` restarts the worker if it exits.

## Cesium integration

Read `snapshot.json` from your local GPT-DOUG backend and convert the supported
layer records to Cesium entities. Keep the `layer_state` and `generated_at`
fields visible so operators can distinguish live, degraded, and stale data.
