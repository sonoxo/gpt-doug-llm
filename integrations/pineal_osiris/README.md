# GPT-Doug PINEAL x OSIRIS — locally integrated visual stack

Uses the official [MIT-licensed OSIRIS source](https://github.com/simplifaisoul/osiris) for the 11 requested map layers. The visual dashboard runs on loopback only; PINEAL receives strictly allowlisted **public feed-health metadata**, not raw coordinates, CCTV, tactical feeds, device IDs or event payloads.

## Run from ANY Mac terminal directory, including ~/Downloads

```sh
curl -fsSLo "$HOME/Downloads/gpt-doug-osiris-bootstrap.sh" 'https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/feature/pineal-osiris-local-clone/integrations/pineal_osiris/bootstrap.sh' && sh "$HOME/Downloads/gpt-doug-osiris-bootstrap.sh"
```

This downloads the inspectable bootstrap script and runs it. It **does not require a git remote in the current directory**. It safely clones or updates a dedicated `~/.local/share/gpt-doug/gpt-doug-llm-osiris` feature checkout and runs `run.sh stack`. Existing unrelated/modified directories are never overwritten.

Prerequisites: Git, Node.js 20.9+ (22 LTS recommended), npm, Python 3.10+, internet on initial install. The launcher prints a specific missing dependency instead of silently installing it. Inspect the downloaded bootstrap shell file first if desired.

The stack checks out official OSIRIS at pin `0aaba3838b550f83eeeaea99e5179d24f85ad65c` into `~/.local/share/gpt-doug/osiris-ui`, checks upstream Git origin and MIT license, runs `npm ci`, and starts Next.js on `127.0.0.1:3000`. It waits for the **process liveness** `/api/health` (not upstream feed health). On an interactive Mac it opens the new **PINEAL / OSIRIS Control Deck** at `http://127.0.0.1:8766/` in your default browser. The control deck is a responsive read-only local webpage with 11 operator-selectable map layers, a one-click launch into the official OSIRIS globe, live process health, strict source freshness classification (ONLINE, DEGRADED, STALE, CLOCK_SKEW and UNAVAILABLE), route provenance, and Pineal SQLite/audit counts. While running the stack refreshes the approved OSIRIS safe-mirror routes every 300 seconds into PINEAL's existing audited ontology memory; unavailable routes are marked degraded or stale, not claimed live. `Ctrl+C` shuts down the managed local server and bridge. No background persistence is created.

Open the local control deck after the server is ready:

`http://127.0.0.1:8766/`

Open OSIRIS's globe directly:

`http://127.0.0.1:3000/?layers=maritime,satellites,cctv,cctv_previews,live_news,earthquakes,global_incidents,day_night,cables,sdk_air,sdk_naval`

Selecting any OSIRIS layer does not guarantee that its API or camera provider is reachable, current, licensed, or configured. The original OSIRIS interface retains its own source limitations and access rules.

## macOS storage recovery (`ENOSPC`)

If the terminal shows `npm warn tar TAR_ENTRY_ERROR ENOSPC: no space left on device`, the Git clones succeeded but npm **could not extract the dependencies onto your Mac**. Repeating `npm ci` without freeing disk space will fail again.

Inspect storage first (safe, non-destructive):

```sh
df -h "$HOME"
du -sh "$HOME/.local/share/gpt-doug/osiris-ui/node_modules" "$HOME/.npm/_cacache" 2>/dev/null || true
```

The standalone recovery script is intentionally runnable **before** updating a local feature-branch checkout, even with a failed install:

```sh
curl -fsSLo "$HOME/Downloads/gpt-doug-osiris-recover.sh" 'https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/feature/pineal-osiris-local-clone/integrations/pineal_osiris/recover.sh'
sh "$HOME/Downloads/gpt-doug-osiris-recover.sh" --check
sh "$HOME/Downloads/gpt-doug-osiris-recover.sh"
```

Recovery validates that `~/.local/share/gpt-doug/osiris-ui` is the **official upstream Git checkout**, refuses symlinked or unexpected source trees, stops if OSIRIS is currently running, deletes only that checkout's incomplete `node_modules` installation, and explicitly clears npm's **regenerable shared download cache**. Clearing the shared cache may make subsequent installs for unrelated projects slower, but does not remove their installed dependencies. Recovery does **not** touch `~/Downloads` project files (apart from its named bootstrap scripts), PINEAL SQLite data, other Git repositories, or your system directories. It requires a recommended 4096 MiB of available disk space before fetching the updated feature branch and resuming the dashboard launch. If disk remains low, it fails with a clear message instead of repeatedly unpacking dependencies. You may need to free more ordinary Mac storage first. The 4 GiB figure is a conservative preflight target, not a guarantee of npm's final footprint.

After the first successful install, a marker is written inside the managed `node_modules` directory; a failed or incomplete npm install is never marked successful. Subsequent starts reuse the completed dependencies unless the lockfile changes.

Once the updated integration is installed you can also run explicit local diagnostics without fetching the standalone recovery script:

```sh
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" disk
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" repair
# To ALSO clear npm's shared download cache, use 'repair-cache' instead.
```

Do not remove unrelated `~/Downloads` files or entire project directories to fix this error. On a smaller Mac disk, an external APFS volume can host the OSIRIS checkout via `OSIRIS_WORKTREE`, but npm's cache may still need space in the home volume unless reconfigured.

## Diagnosis and operations

Run these from anywhere after bootstrap:

```sh
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" doctor
sh "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris/integrations/pineal_osiris/run.sh" status
```

The launcher also supports `disk` (storage check), `repair` (explicit OSIRIS-only partial dependency cleanup), `repair-cache` (also clear shared npm cache), `url` (map link), `console` (control deck link), `run` (visual only), `sync` (one public feed-health import), `stack` (normal integrated foreground mode), and `help`. To use another port, run with `OSIRIS_PORT=3005` set in the environment. Change the control deck port separately with `PINEAL_OSIRIS_CONSOLE_PORT=8767`. Optional `OSIRIS_SYNC_INTERVAL=300` is bounded to 120–3600 seconds. `OSIRIS_NO_BROWSER=1` disables automatic browser opening.

PINEAL's local ontology can be inspected by running:

```sh
cd "$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris"
PYTHONPATH=integrations/gpt-doug-pineal/src python3 -m pineal.cli find osiris --namespace osiris_feed
```

## Visual control deck and state truth

The local HTTP server binds **only** to `127.0.0.1`, uses an explicit Host allowlist, serves only three static assets and `GET /api/status`, exposes no write endpoint, and applies a strict Content Security Policy. It does not proxy the live map or copy OSIRIS's recon endpoints. You can select any subset of the 11 visual layers, then open the chosen upstream globe URL.

The status API re-evaluates mirror timestamps **at read time**: an old successful request is labeled `STALE`, not `ONLINE`. The OSIRIS `/api/health` endpoint is explicitly only process liveness. The console counts existing PINEAL SQLite records with a read-only connection and does not disclose record values, private data, or secrets. Audit counts **are not** claims that integrity was re-verified. No snapshot or database is created by a status read.

The console is available only while the integrated foreground stack is running. It does not install a permanent daemon or public network listener. The globe remains accessible directly at the chosen map port. Use `Ctrl+C` to shut down both the local OSIRIS process and the console.

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

The offline suite verifies ENOSPC preflight and isolated cleanup behavior, working-directory independence, strict HTTP Host and CSP controls, static asset delivery, feed freshness, untrusted timestamp handling, SQLite read-only metrics, schema filtering, and idempotent Pineal ontology updates. Local OSIRIS boot, third-party feed health and browser rendering still require an internet-connected operator machine; they cannot be claimed verified by offline tests.
