# GPT-Doug-PINEAL x OSIRIS (local open-source clone)

This integration runs the original [MIT-licensed OSIRIS](https://github.com/simplifaisoul/osiris) dashboard locally at a reviewed, pinned source revision, with the 11 map-layer switches supplied by the operator. It optionally imports **only approved public route health metadata** to the already-existing local PINEAL ontology memory. It does not copy upstream proprietary infrastructure or change the existing safe-mirror permissions.

## Run (Mac/Linux)

From the GPT-Doug repository root:

```sh
sh integrations/pineal_osiris/run.sh doctor
sh integrations/pineal_osiris/run.sh run
```

The launcher requires Git, Node.js 20+ and npm. It checks out OSIRIS commit `0aaba3838b550f83eeeaea99e5179d24f85ad65c` in `~/.local/share/gpt-doug/osiris-ui`, checks upstream origin, refuses modified worktrees, installs dependencies with `npm ci`, then starts Next.js bound to `127.0.0.1:3000`. Network access is needed for initial cloning and dependencies. Read upstream's MIT LICENSE and privacy/security guidance.

The launcher prints the selected-layers URL; you can also print it without running anything:

```sh
sh integrations/pineal_osiris/run.sh url
```

The upstream dashboard controls the 11 visual toggles: maritime, satellites, CCTV, CCTV previews, live news, earthquakes, global incidents, day/night, cables, SDK air, and SDK naval. Selecting a layer does not guarantee that its upstream provider is live, permitted, configured, or accessible.

## Opt-in PINEAL health sync

In a second terminal, with the OSIRIS application running, execute:

```sh
sh integrations/pineal_osiris/run.sh sync
```

This triggers the pre-existing `integrations/osiris_mirror/osiris_mirror.py --once` local allowlist, then imports only the snapshot's sanitized metadata into PINEAL's `osiris_feed` namespace with provenance, freshness flags and audit logging. It will not mirror raw coordinates, traffic tracks, CCTV images, telemetry payloads, or intelligence records. Only `health`, `earthquakes`, `fires`, `weather`, `air-quality`, `space-weather`, `news`, `live-news`, `gdelt` and `markets` health states are eligible, consistent with the existing restricted mirror. `global_incidents` is not imported as incident records. The importer uses versioned upserts to avoid duplicate memory entries.

Inspect the sanitized snapshot without changing memory:

```sh
python3 integrations/pineal_osiris/bridge.py --dry-run
```

Read saved ontology records:

```sh
PYTHONPATH=integrations/gpt-doug-pineal/src python3 -m pineal.cli find osiris --namespace osiris_feed
```

`sync` is an explicit one-shot operation, not an indefinite agent or background process. Upstream raw visual layers remain subject to applicable terms, operator permissions, and source freshness.

## Offline tests

```sh
sh -n integrations/pineal_osiris/run.sh
python3 -m unittest discover -s integrations/pineal_osiris -p 'test_*.py' -v
```

The five offline regression tests cover route allowlisting, filtering coordinates and tracking payloads, reject-untrusted-input behavior, stale/clock-skew flags, and idempotent/updating writes. A live end-to-end run requires internet access and upstream availability. Do not represent an unavailable or cached data source as currently live.
