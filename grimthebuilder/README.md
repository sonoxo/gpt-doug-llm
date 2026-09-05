# GrimTheBuilder — XUNIA HQ Integration

GrimTheBuilder is the browser IDE/program. Its new full-stack, self-hostable source now lives in [`../grimthebuilder-app/`](../grimthebuilder-app/). This `grimthebuilder/` directory remains the XUNIA connection/export surface and is **not** the application source.

## Current runtime state
- Current live runtime: https://orbit-code-studio.almighty-son-8109.chatgpt.site/
- Current `hello-world` workspace: https://orbit-code-studio.almighty-son-8109.chatgpt.site/?project=9a63cd65-e102-4241-a46b-14925468bec2
- Full-stack source: https://github.com/sonoxo/gpt-doug-llm/tree/main/grimthebuilder-app
- CI gate: `.github/workflows/grimthebuilder-app.yml`
- XUNIA HQ: https://xunia.org/
- XUNIA launcher: https://xunia.org/grimthebuilder

The Orbit deployment remains the live endpoint only until the new full-stack container is deployed and its health/runtime tests pass. At that point the XUNIA launcher and manifests can cut over to the self-hosted runtime.

## This integration folder contains
- exported workspace files and experiments
- XUNIA connection metadata
- GitHub Pages launcher/mirror assets

## Application source implements
- persistent projects and files
- Monaco editor
- real shell/process runtime
- Node/npm/pnpm/Python/Git execution
- live static and backend preview
- checkpoints/rollback
- AI build/fix/plan/explain endpoint
- Docker runtime
- regression + container health tests

## Flow

`XUNIA HQ → GrimTheBuilder IDE → project filesystem/runtime → preview → Git/deploy`

`hello-world` remains a workspace inside GrimTheBuilder, never the GrimTheBuilder application itself.
