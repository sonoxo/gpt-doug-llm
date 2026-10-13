# GPT-Doug TAK-OS — 100% free synthetic operations console

A standalone, responsive geospatial **civilian exercise simulator**, independent of official TAK products. **Every asset, position, event and metric is synthetic.** It does **not** connect to official TAK Server or mission systems; no government sponsorship or authorization is implied.

## Free browser installation

Once this pull request merges and the existing XUNIA GitHub Pages deployment succeeds, open:

**https://xunia.org/tak-os/**

Or launch without cloud hosting, from the `docs/tak-os` directory:

```sh
sh start.sh web
```

Then navigate to http://127.0.0.1:8080. Python 3 is the only requirement for the local server. The dashboard is a single standalone HTML document with no external JavaScript or stylesheet dependencies. It works offline with its vector map. Map tiles are optional and load from OSM only when the switch is enabled and a network is available.

## Simulator contents

- Twelve synthetic civilian response, marine, aerial and weather assets
- Movable/zoomable grid and optional OpenStreetMap tiles; local annotation pins
- Pausable, resettable trajectory simulation and 1x/2x/4x/8x time controls
- Event queue, new exercise incidents, manual acknowledgment and timeline filtering
- JSON/CSV exports, typed entity provenance/ontology, local CoT XML inspector
- QEMU VM configuration preview, optional Docker Compose service, bounded host operation
- Responsive desktop/mobile design and offline-install metadata (PWA)
- Resource catalog and XUNIA front-page entries; dependency-free CI smoke tests

## Optional local Ubuntu VM

The browser alone is sufficient. If you specifically want a VM, read [vm/README.md](vm/README.md).

For x86_64 Linux hosts with QEMU already installed and an official Ubuntu ISO:

```sh
cd docs/tak-os/vm
sh launch.sh /absolute/path/to/ubuntu-server.iso
```

This **starts QEMU on the operator's host** (with a new guest disk if needed). It is not executed by ChatGPT or the public website. The script forwards only SSH over host loopback. Install OpenSSH in the guest. After copying `docs/tak-os` into Ubuntu, serve it inside guest with `sh start.sh web` and use an SSH tunnel on host: `ssh -p 2222 -N -L 8080:127.0.0.1:8080 USER@127.0.0.1`. See full [VM runbook](vm/README.md) for details, including macOS/UTM guidance.

## Optional free container

```sh
cd docs/tak-os
sh start.sh docker
# Stop: docker compose down
```

Uses an unprivileged Nginx container, read-only filesystem, dropped capabilities, and binds HTTP only to `127.0.0.1:8080`. Docker/Compose is optional; Docker image pulls need Internet access.

## Tests

From repository root:

```sh
python3 -m unittest discover -s tests -p 'test_tak_os_static.py' -v
```

The PR also runs the standalone `tak-os-free.yml` syntax, dependency, contract and HTTP tests on public GitHub Actions runners. No cloud VM, commercial provider, token, or paid API is required.

## Security and licensing boundary

- CoT sample inspector is a local XML demo and rejects DTD/ENTITY inputs; it is not an authenticated CoT receiver.
- No real tactical GPS feeds, messaging, intelligence, camera telemetry or command/control operations are implemented.
- No API secrets, third-party JavaScript, or broad public listening endpoints.
- OpenStreetMap tiles are governed by [OSM usage policy](https://operations.osmfoundation.org/policies/tiles/); preserve attribution. Offline grid requires no tile requests.
- Browser offline cache stores **public app-shell assets only**, not operational data or OSM map tiles.
- Actual TAK products have [official usage/authority requirements](https://tak.gov/products) distinct from this independent demonstration.

**Independent demonstration • synthetic data only • not TAK Product Center software.**
