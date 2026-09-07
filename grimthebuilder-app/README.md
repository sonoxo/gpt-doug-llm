# GrimTheBuilder — Local Runtime / Integration Artifact

The canonical **GrimTheBuilder application** is the XUNIA browser IDE/program currently hosted at:

https://orbit-code-studio.almighty-son-8109.chatgpt.site/

This `grimthebuilder-app/` directory is the repository-backed local workspace, export, self-hosting, and integration runtime. It now includes an actual GPT Doug connector UI rather than relying on undocumented settings.

## Implemented

- multi-project persistent workspace storage
- safe project filesystem with traversal protection and file-size limits
- Monaco editor with browser fallback
- live static preview and reverse-proxied backend preview
- real project shell over WebSocket
- real Node/npm/pnpm/Python/Git process execution through an allowlist
- automatic project run detection
- checkpoints and rollback
- AI BUILD/FIX/PLAN/EXPLAIN endpoint
- visible **GPT DOUG SETTINGS** control in the Grim Agent panel
- direct browser connection to the Wakeup3LM bridge
- `/health` readiness check and `/api/tags` model discovery
- non-streaming `/api/chat` requests using the selected local model
- bounded project context and structured file-operation output
- client validation for operation count, file size, path traversal, absolute paths, and `.grim` access
- automatic checkpoint before GPT Doug writes or deletes project files
- bearer token retained only in browser session storage
- deterministic local builder fallback
- Docker image, health endpoint, and Node regression tests

## Run

```bash
cd grimthebuilder-app
npm install
npm start
```

Open `http://localhost:8787`.

Or:

```bash
docker compose up --build
```

## Connect GPT Doug

Start Ollama and install the model served by the bridge. From the repository root, allow the exact browser origin that will open GrimTheBuilder.

For the local runtime:

```bash
DOUG_BRIDGE_ORIGINS=http://localhost:8787 python3 -m wakeup3lm.bridge
```

For the current hosted Orbit origin:

```bash
DOUG_BRIDGE_ORIGINS=https://orbit-code-studio.almighty-son-8109.chatgpt.site python3 -m wakeup3lm.bridge
```

Then:

1. Open the **Grim Agent** panel.
2. Click **GPT DOUG SETTINGS**.
3. Keep `http://127.0.0.1:8791` for a bridge running on the same computer.
4. Enter a bearer token only when the bridge was started with `DOUG_BRIDGE_TOKEN`.
5. Click **CONNECT & DISCOVER MODELS**.
6. Select **GPT Doug local bridge** as the agent provider and run a BUILD, FIX, PLAN, or EXPLAIN request.

The browser calls the local bridge directly. The application server never tries to interpret its own `127.0.0.1` as the user's computer.

A secure hosted page can still be subject to browser local-network or mixed-content policy. The bridge supports exact-origin CORS and Private Network Access preflight. Where a browser blocks loopback access, expose the bridge through an HTTPS endpoint, use a bearer token of at least 24 characters, and enter that HTTPS base URL in the connector.

## Connector data handling

- Bridge URL and selected model are stored in local storage.
- Bearer token is stored only in session storage and is cleared when disconnected.
- Project context is capped before it is sent to the model.
- PLAN and EXPLAIN modes reject returned file operations.
- BUILD and FIX create a project checkpoint before applying changes.
- GPT Doug responses must be JSON file operations with complete file contents.

## Validation

```bash
npm run check
npm test
```

## Security boundary

This runtime executes project code and is intended for an owner-controlled development host. A public multi-user deployment must isolate each project in a dedicated sandbox and add authentication before exposing runtime endpoints to arbitrary users.

The connector does not bypass model restrictions, provider quotas, browser network policy, or bridge authentication. It only connects GrimTheBuilder to a model service the operator already controls.
