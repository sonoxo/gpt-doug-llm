# GPT-DOUG TAK-OS — complete free end-to-end LOCAL lab

**Status: working independent civilian synthetic lab. No live TAK.gov, military, government, or third-party systems connected.** This is not a substitute for TAK Server, WebTAK, ATAK, WinTAK, or TAKX and is not an official TAK Product Center product.

## One-command launch (Mac, Linux, Windows with Python)

From the project folder:

```sh
cd docs/tak-os
sh start.sh web
```

Open **http://127.0.0.1:8080**. Requires only free Python 3. No paid API, subscription, database server, Node installation, or Docker is needed.

Full data path in this local deployment:

```
Synthetic responder simulator ─┐
Browser CoT XML inspector ─────┼──> Local CoT 2.0 gateway (Python stdlib)
Legacy CoT UDP/TCP loopback ──┘                     │
                                                    ├── SQLite event log + human ACK
                                                    ├── HTTP JSON snapshot, health and XML export
                                                    └── SSE live event stream ──> browser map / event panel
```

The real TAK interface remains OFFLINE. Browser fallback continues working if the Python gateway is not started.

## Runtime options

| Command | Behavior |
| --- | --- |
| `sh start.sh web` | Full local Python CoT XML / SQLite / SSE gateway + browser UI on 127.0.0.1:8080 |
| `sh start.sh static` | Browser-only synthetic demo; no backend persistence |
| `sh start.sh legacy-udp` | Full gateway + legacy CoT XML UDP listener on **127.0.0.1:6969** |
| `sh start.sh legacy-tcp` | Full gateway + legacy CoT XML TCP listener on **127.0.0.1:8087** |
| `sh start.sh docker` | Build and launch optional local read-only non-root Docker gateway (host publishes only loopback) |
| `sh start.sh test` | Run dependency-free CoT, HTTP, SQLite, legacy UDP/TCP and SSE tests |

Set `TAK_OS_PORT=18900` to choose a different local HTTP port; it must be 1024–65535. Persistent SQLite logs default to `~/.local/state/gpt-doug-tak-os/gateway.sqlite3`; set `TAK_OS_DB=/safe/local/path/events.sqlite3` to change it. The directory must be writable by your local user.

### Launch from a fresh clone or existing GPT-Doug repository

The TAK-OS code is on [PR #365](https://github.com/sonoxo/gpt-doug-llm/pull/365) until merged. In an existing Git clone:

```sh
git fetch origin feat/free-tak-os-simulator
git switch -C feat/free-tak-os-simulator FETCH_HEAD
cd docs/tak-os
sh start.sh web
```

If you have no checkout, `git clone --single-branch --branch feat/free-tak-os-simulator https://github.com/sonoxo/gpt-doug-llm.git` first, then `cd gpt-doug-llm/docs/tak-os` and `sh start.sh web`. All commands run on **your** computer; ChatGPT does not install software on the operator's machine.

## Browser capabilities

- Interactive 2D map with **12 browser-simulated units and six additional gateway-simulated CoT units**, animated track history, optional OpenStreetMap tiles and offline vector fallback
- Pause/resume/speed control for the browser simulation; gateway positions stream on their own 1.5-second heartbeat
- Browser asset inspector with source provenance (synthetic vs. unverified), search/filter, annotation pins and response zone overlay
- Data Feeds: validate, ingest and export CoT 2.0 XML; live gateway status; persistent local incident queue with acknowledgment
- SQLite logs, `/api/v1/health`, `/api/v1/session`, `/api/v1/snapshot`, `/api/v1/events`, `/api/v1/stream` (SSE), `/api/v1/cot.xml?uid=LAB-RESCUE-01`
- Human-readable VM launch preview, offline PWA shell, responsive desktop/mobile layout, JSON/CSV export and local typed ontology view

### API example (local lab only)

Gateway requests that change data need the current local session token and a same-origin request. The UI fetches the session token automatically when served from the local gateway; **do not insert tokens or private certificates into the public browser application**.

A lab sender can POST XML from its own localhost client. For manual local testing, use Python:

```python
import json, urllib.request
base = 'http://127.0.0.1:8080/api/v1/'
session = json.load(urllib.request.urlopen(base+'session'))
xml = urllib.request.urlopen(base+'cot.xml?uid=LAB-RESCUE-01').read()
req = urllib.request.Request(base+'cot', data=xml, method='POST', headers={
    'Content-Type': 'application/xml',
    'X-TAK-OS-Token': session['csrfToken'],
})
print(json.load(urllib.request.urlopen(req)))
```

This validates `CoT XML -> REST -> SQLite -> SSE -> Map`. There is no transmission to TAK.gov or an operational server.

For UDP legacy loopback, start `sh start.sh legacy-udp`. A Python process can then `socket.sendto(cot_xml, ('127.0.0.1', 6969))`. For TCP, start `sh start.sh legacy-tcp` and send one complete `<event>...</event>` XML element to localhost port 8087, then close. These are **local-only demo listeners**, not secure internet listeners.

## Optional Docker and VM

`sh start.sh docker` builds a tiny Python 3 container with no additional Python packages. It uses an unprivileged user, read-only root filesystem, dropped Linux capabilities, a writable named SQLite volume, and a port bound to `127.0.0.1`. Check `Dockerfile`, `compose.yaml`, and `docker compose logs --tail=60` when troubleshooting. Local CPU/disk/network use may still have costs to the operator, but there is no required hosting subscription.

See [vm/README.md](vm/README.md) for QEMU/KVM and free UTM / Ubuntu guest instructions. Keep the gateway bound to guest localhost and access through **authenticated SSH forwarding**; don't directly expose port 8080 to a network.

## Tests

```sh
python3 -m unittest discover -s tests -p 'test_tak_os_gateway.py' -v
python3 -m unittest discover -s tests -p 'test_tak_os_static.py' -v
node --check docs/tak-os/app.js
node --check docs/tak-os/bridge.js
node --check docs/tak-os/sw.js
```

Run those from the **repository root**. Browser tests are optional and run with Playwright/Chromium if installed, without third-party runtime JS or paid services.

## Limits and authority

- **No real TAK Server session has been authenticated or tested.** This gateway is a local compatibility lab, not a drop-in replacement for TAK Server.
- No automatic TAK.gov scraping, site modification, certificate enrollment, password handling, or elevation of privileges. Public documentation and official open-source code serve as engineering references only.
- Input UIDs starting with `DEMO-` / `LAB-` are accepted by default. The optional `--allow-unverified-lab-input` mode remains strictly local, visibly unverified, and never forwards data outside the host.
- Do not use the unencrypted legacy loopback inputs on untrusted network interfaces, nor treat this as an authorized live tactical system.
- Live TAK product integration requires a **separate** identity/permission review, the appropriate organizational authority to operate (ATO), documented access to an owned or explicitly authorized TAK Server, and mutually authenticated TLS with validated certs. Nothing in this project circumvents that process.
- Copyright/export/reuse conditions for actual TAK products remain controlled by their respective owners. No TAK proprietary components are redistributed here.
- Optional OSM tiles are subject to [OSM policy](https://operations.osmfoundation.org/policies/tiles/) and attribution. The app supports disabling tiles and offline visualization.

Official references: [TAK.gov](https://tak.gov/), [TAK products](https://tak.gov/products), [TAK usage FAQ](https://tak.gov/faq), [open-source TAK Server](https://github.com/TAK-Product-Center/Server) and its [CoreConfig example](https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/example/CoreConfig.example.xml).

**Independent demonstration · synthetic data by default · not TAK Product Center software.**
