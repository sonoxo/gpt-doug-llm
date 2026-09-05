# GrimTheBuilder — XUNIA HQ Integration

GrimTheBuilder is the owner-private Orbit browser IDE/program hosted at:

- https://orbit-code-studio.almighty-son-8109.chatgpt.site/
- Current `hello-world` workspace: https://orbit-code-studio.almighty-son-8109.chatgpt.site/?project=9a63cd65-e102-4241-a46b-14925468bec2

The `grimthebuilder/` directory is only the XUNIA connection/export surface. It is **not** the GrimTheBuilder application source.

The separate `grimthebuilder-app/` directory and `ghcr.io/sonoxo/grimthebuilder:latest` image are a noncanonical rebuild/runtime experiment created while testing self-hosting. They must not be presented as the actual GrimTheBuilder program unless the canonical Orbit source is explicitly migrated into that codebase and visually/functionally verified against the owner runtime.

## Canonical UI/runtime identity
The canonical GrimTheBuilder program is the Orbit IDE with:
- Workspaces sidebar
- multi-file editor tabs
- Run control
- Console
- Preview / Agent / Team / Deploy panes
- browser sandbox / isolated browser execution

## Current source status
- Canonical application source repository: **not yet recovered/verified**
- XUNIA HQ launcher: https://xunia.org/grimthebuilder
- XUNIA launcher must point to the Orbit runtime until the exact canonical source is recovered and migrated.

## Integration artifacts
This folder may contain:
- exported workspace files
- XUNIA connection metadata
- GitHub Pages launchers/mirrors

`hello-world` remains a workspace inside GrimTheBuilder, never the GrimTheBuilder application itself.

## Correct flow

`XUNIA HQ → canonical Orbit GrimTheBuilder IDE → workspace/project → exported GitHub artifacts`
