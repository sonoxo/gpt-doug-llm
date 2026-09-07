# PALANTIR TOOLBOX // GPT-DOUG

A real Manifest V3 Chrome extension for an **authorized Palantir Foundry environment**. The extension is an independent GPT-DOUG ecosystem tool; it is not a Palantir product and does not create tenant access, credentials, permissions, licenses, or authorization.

## What works in v0.1

- secure localhost bridge to the repository's existing `palantir_foundry.py` client;
- direct short-lived bearer-token mode for supported Foundry tenants;
- connection/health check;
- list Ontologies via `/api/v2/ontologies`;
- list Ontology object types;
- list objects for an object type;
- search-object client wiring;
- browser selection capture for A.E.O. / RVIA provenance workflows;
- session-only browser storage for bridge keys and direct bearer tokens;
- exact `*.palantirfoundry.com` direct-origin restriction;
- local bridge bound to `127.0.0.1` only;
- read-first bridge: Foundry Actions are intentionally not exposed.

The endpoint shapes mirror the hardened repository client in [`palantir_foundry.py`](../../palantir_foundry.py).

## Recommended architecture

```text
Chrome extension
      │
      │ localhost + bridge key
      ▼
127.0.0.1:8765
Palantir Toolbox Bridge
      │
      │ credentials remain in process environment
      ▼
palantir_foundry.py
      │
      │ HTTPS + same-host redirect policy
      ▼
AUTHORIZED FOUNDRY TENANT
      │
      └── Ontology read/search APIs
```

## 1. Configure Foundry in your terminal

Use either a pre-issued token or OAuth client credentials already authorized for your tenant.

### Token mode

```bash
export FOUNDRY_BASE_URL="https://YOUR-TENANT.palantirfoundry.com"
export FOUNDRY_TOKEN="YOUR_SHORT_LIVED_TOKEN"
export PALANTIR_TOOLBOX_BRIDGE_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

### OAuth client-credentials mode

```bash
export FOUNDRY_BASE_URL="https://YOUR-TENANT.palantirfoundry.com"
export FOUNDRY_CLIENT_ID="..."
export FOUNDRY_CLIENT_SECRET="..."
export FOUNDRY_SCOPES="api:ontologies-read"
export PALANTIR_TOOLBOX_BRIDGE_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Do **not** place any credential in this repository.

## 2. Start the bridge

From the repository root:

```bash
python3 tools/palantir-toolbox/bridge/palantir_bridge.py
```

Expected startup output:

```text
Palantir Toolbox bridge: http://127.0.0.1:8765
Foundry host: YOUR-TENANT.palantirfoundry.com
Mode: read-first; action writes are not exposed by this bridge
```

## 3. Load the Chrome extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select `tools/palantir-toolbox/`.
5. Open the extension popup.
6. Keep **Local secure bridge** selected.
7. Paste the same `PALANTIR_TOOLBOX_BRIDGE_KEY` into **Bridge key**.
8. Select **Test connection**.
9. Use **List ontologies**, then enter an Ontology API name to inspect object types and objects.

## Direct mode

Direct mode exists for short-lived testing when browser access is appropriate for your deployment. The token is stored only in `chrome.storage.session`, not `chrome.storage.local`. The origin must be HTTPS and end in `.palantirfoundry.com`.

For normal use, prefer the local bridge so Foundry credentials stay out of the browser.

## A.E.O. / RVIA capture

Highlight text on a public webpage, right-click, then choose **Capture selection to Palantir Toolbox**. The extension stores the selection, page URL, page title, and capture timestamp in the current browser session. This is a source-intake primitive; it does not assert that the captured claim is true.

## Security boundary

This build is deliberately read-first. It does not expose Foundry Action execution through the localhost bridge. Future write modules must preserve the repository rule:

`AI proposes → Ontology grounds → policy bounds → explicit approval → action executes → evidence records result`

The bridge refuses to start without a bridge key, accepts only Chrome-extension origins, binds only to localhost, and relies on the existing Foundry client's HTTPS/host pinning and write-disable controls.

## Next real modules

The same extension shell is intended to host Ontology Lens, AIP Sidecar, Evidence Capture, Ontology Graph Peek, AIP Analyst Launcher, MCP Bridge, Pipeline Watcher, Apollo Release Radar, OSDK Inspector, and the consolidated GPT-DOUG Palantir Command Deck. Each module must be backed by a documented API or an authorized local adapter before being marked implemented.
