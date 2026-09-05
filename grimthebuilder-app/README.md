# GrimTheBuilder — Local Runtime / Integration Artifact

The canonical **GrimTheBuilder application** is the XUNIA browser IDE/program hosted at:

https://orbit-code-studio.almighty-son-8109.chatgpt.site/

This `grimthebuilder-app/` directory is a **local workspace, export, self-hosting, and integration artifact** used to develop, test, and connect GrimTheBuilder capabilities with the XUNIA ecosystem. It is **not the canonical GrimTheBuilder application itself**, and it is not the old `hello-world` export.

## Implemented in this local integration runtime

- multi-project persistent workspace storage
- safe project filesystem with traversal protection and file-size limits
- Monaco editor with browser fallback
- live static preview and reverse-proxied backend preview
- real project shell over WebSocket (stdin/stdout/stderr)
- real Node/npm/pnpm/Python/Git process execution through an allowlist
- automatic project run detection for Next.js, Vite, generic Node, and Python
- per-project process limits, timeout, stop, logs, and dynamic preview ports
- checkpoints and rollback with automatic pre-restore backup
- AI BUILD/FIX/PLAN/EXPLAIN endpoint with an optional model provider
- zero-cost deterministic local builder fallback when no model is configured
- Docker image + persistent data volume
- health endpoint and Node regression tests
- XUNIA HQ link in the local integration runtime

## Run the local integration artifact

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

Launching this local artifact does not replace or redefine the canonical hosted GrimTheBuilder application.

## Validation

```bash
npm run check
npm test
```

## Security boundary

This local runtime executes project code. The default implementation is appropriate for an owner-controlled development host. A public multi-user deployment must place each project in a stronger sandbox boundary such as a dedicated container/VM/gVisor/Firecracker worker and add authentication before exposing runtime endpoints to arbitrary users.

## XUNIA flow

`XUNIA HQ → canonical GrimTheBuilder IDE → workspace/export/integration artifacts → project filesystem/runtime → preview → Git/deploy`

The existing `hello-world`, `grimthebuilder/`, `grimthebuilder-app/`, and `docs/grimthebuilder/` paths are workspace/export/local-runtime/integration surfaces. They are not the canonical GrimTheBuilder application.
