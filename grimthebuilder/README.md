# GrimTheBuilder — XUNIA Browser IDE

GrimTheBuilder is now a self-hosted, dependency-free browser IDE deployed through the `gpt-doug-llm` GitHub Pages surface and connected to XUNIA HQ.

## Canonical links
- GrimTheBuilder runtime: https://sonoxo.github.io/gpt-doug-llm/grimthebuilder/
- XUNIA HQ: https://xunia.org/
- XUNIA launcher route: https://xunia.org/grimthebuilder
- Repository: https://github.com/sonoxo/gpt-doug-llm/tree/main/grimthebuilder

## Runtime capabilities
- HTML editor
- CSS editor
- JavaScript editor
- live iframe preview
- browser console bridge for logs and runtime errors
- browser-local autosave
- JSON workspace import/export
- desktop/mobile preview modes
- keyboard run shortcut (`Cmd/Ctrl + S`)
- XUNIA HQ navigation

## Architecture

`XUNIA HQ → /grimthebuilder → GitHub Pages runtime → local browser workspace → preview/export`

The working Pages implementation lives in `docs/grimthebuilder/`. The top-level `grimthebuilder/` path remains as an integration/fallback surface so either common GitHub Pages source layout resolves to the functional IDE.

## Persistence

Workspaces persist in browser `localStorage` under `grimthebuilder.workspace.v1`. Exported project snapshots are JSON and can be re-imported later.

## Legacy runtime

The former Orbit Code Studio workspace is retained only as a legacy link inside the IDE. It is no longer the canonical GrimTheBuilder runtime.

## Status

**SELF-HOSTED RUNTIME: IMPLEMENTED**  
**XUNIA ROUTE: CONNECTED**  
**PRIMARY DEPLOYMENT: GITHUB PAGES**
