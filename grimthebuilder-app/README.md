# GrimTheBuilder — Full-Stack Runtime v1

GrimTheBuilder is the XUNIA browser IDE/program. This directory is the new self-hostable full-stack implementation; it is **not** the old `hello-world` export.

## Implemented

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
- XUNIA HQ link in the IDE

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

## Validation

```bash
npm run check
npm test
```

## Security boundary

This runtime executes project code. The default implementation is appropriate for an owner-controlled development host. A public multi-user deployment must place each project in a stronger sandbox boundary such as a dedicated container/VM/gVisor/Firecracker worker and add authentication before exposing runtime endpoints to arbitrary users.

## XUNIA flow

`XUNIA HQ → GrimTheBuilder IDE → project filesystem/runtime → preview → Git/deploy`

The existing `grimthebuilder/` and `docs/grimthebuilder/` paths remain launcher/export/integration surfaces. They are not the application source.
