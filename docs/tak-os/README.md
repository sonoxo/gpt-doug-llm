# GPT-DOUG TAK-OS — Free browser demo

An independent, civilian, **synthetic-data-only** virtual operations dashboard. Not official TAK software. Real TAK endpoints remain disconnected.

## Free browser launch

Open `docs/tak-os/index.html` directly in a modern browser or serve it locally:

```sh
cd docs/tak-os
python3 -m http.server 8080 --bind 127.0.0.1
```

Then navigate to http://127.0.0.1:8080.

## Features

- Moving synthetic civilian responder/observation markers; optional OpenStreetMap interactive viewport tiles
- Asset search, type filters, pan/zoom, click-to-annotate, inspect selected asset
- Pause, resume and adjustable simulated speed
- Timestamped fictional incident timeline with human ACK action
- JSON scenario export, CSV event export and event-generation buttons
- CoT XML example parser that rejects DTD/entity declarations, with no network transmission
- Synthetic ontology entity counts and QEMU/KVM VM configuration examples

## VM-free or VM-backed use

A VM is not needed for the static dashboard. If desired, install a free Ubuntu guest using QEMU/KVM or UTM, copy this directory into the guest and serve it on 127.0.0.1:8080. SSH local port forwarding is recommended for host access. Browser controls do not provision or operate a real VM.

No cloud account, API token, subscription, paid service, or real GPS data is needed. Optional map tiles use volunteer-run OpenStreetMap infrastructure, with attribution. Observe [tile usage rules](https://operations.osmfoundation.org/policies/tiles/). Turn off tiles to use the built-in grid offline.

## Verification

This single HTML file is portable and does not use external JS or CSS dependencies. All telemetry is generated in-browser. Do not add live CoT traffic, credentials or sensitive operational data to this public demo. Review official TAK licensing and operating authority separately for real TAK products.

Independent demonstration — not affiliated with or endorsed by the TAK Product Center or the U.S. Government.
