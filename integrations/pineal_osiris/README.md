# GPT-Doug PINEAL x OSIRIS — locally integrated visual stack

Uses the official [MIT-licensed OSIRIS source](https://github.com/simplifaisoul/osiris) for the 11 requested map layers. The visual dashboard runs on loopback only; PINEAL receives strictly allowlisted **public feed-health metadata**, not raw coordinates, CCTV, tactical feeds, device IDs or event payloads.

## Run from ANY Mac terminal directory, including ~/Downloads

```sh
curl -fsSLo "$HOME/Downloads/gpt-doug-osiris-bootstrap.sh" 'https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/feature/pineal-osiris-local-clone/integrations/pineal_osiris/bootstrap.sh' && sh "$HOME/Downloads/gpt-doug-osiris-bootstrap.sh"
```

This downloads the inspectable bootstrap script and runs it. It **does not require a git remote in the current directory**. It safely clones or updates a dedicated `~/.local/share/gpt-doug/gpt-doug-llm-osiris` feature checkout and runs `run.sh stack`. Existing unrelated/modified directories are never overwritten.

Prerequisites: Git, Node.js 20.9+ (22 LTS recommended), npm, Python 3.10+, internet on initial install. The launcher prints a specific missing dependency instead of silently installing it. Inspect the downloaded bootstrap shell file first if desired.

The stack checks out official OSIRIS at pin `0aaba3838b550f83eeeaea99e5179d24f85ad65c` into `~/.local/share/gpt-doug/osiris-ui`, checks upstream Git origin and MIT license, runs `npm ci`, and starts Next.js on `127.0.0.1:3000`. It waits for the **process liveness** `/api/health` (not upstream feed health). On an interactive Mac it opens the selected URL in your default browser. While running it refreshes the approved OSIRIS safe-mirror routes every 300 seconds into PINEAL's existing audited ontology memory; unavailable routes are marked degraded or stale, not claimed live. `Ctrl+C` shuts down the managed local server and bridge. No background persistence is created.

Open the visual UI after the server is ready:

`http://127.0.0.1:3000/?layers=maritime,satellites,cctv,cctv_previews,live_news,earthquakes,global_incidents,day_night,cables,sdk_air,sdk_naval`

Selecting any OSIRIS layer does not guarantee that its API or camera provider is reachable, current, licensed, or configured. The original OSIRIS interface retains its own source limitations and access rules.

## Diagnosis and operations

Run these from anywhere after bootstrap:

```sh
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" doctor
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" status
```

The launcher also supports `url`, `run` (visual only), `sync` (one public feed-health import), `stack` (normal integrated foreground mode), and `help`. To use another port, run with `OSIRIS_PORT=3005` set in the environment. Optional `OSIRIS_SYNC_INTERVAL=300` is bounded to 120–3600 seconds. `OSIRIS_NO_BROWSER=1` disables automatic browser opening.

PINEAL's local ontology can be inspected by running:

```sh
cd "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris"
PYTHONPATH=integrations/gpt-doug-pineal/src python3 -m pineal.cli find osiris --namespace osiris_feed
```

## Feed access boundary

`osiris_mirror.py` allows only `health`, `earthquakes`, `fires`, `weather`, `air-quality`, `space-weather`, `news`, `live-news`, `gdelt` and `markets`. `bridge.py` additionally rechecks the exact allowlist and source schema, storing each route's status, last-check timestamp, latency, digest and evidence label as PINEAL ontology facts. Raw source JSON is **never** imported into memory.

| OSIRIS share URL layer | Visual UI | PINEAL metadata |
| --- | --- | --- |
| `maritime`, `satellites`, `cctv`, `cctv_previews`, `sdk_air`, `sdk_naval` | Upstream visual, if available | Not mirrored |
| `live_news`, `earthquakes` | Upstream visual, if available | Health/provenance only |
| `global_incidents` | Upstream visual, if available | Only approved `gdelt` feed health; no incidents |
| `day_night`, `cables` | Upstream visual | Not mirrored |

## Offline validation

```sh
sh -n integrations/pineal_osiris/run.sh integrations/pineal_osiris/bootstrap.sh
python3 -m unittest discover -s integrations/pineal_osiris -p 'test_*.py' -v
```

The offline suite verifies working-directory independence, feed-health semantics, schema filtering, and idempotent Pineal ontology updates. Local OSIRIS boot, third-party feed health and browser rendering still require an internet-connected operator machine; they cannot be claimed verified by offline tests.
