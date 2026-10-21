# GPT-Chaos // REA Kraken Swarm

The upstream project is https://github.com/morluto/rea (MIT). This adapter uses the official REA local CLI for operator-authorized JavaScript/Electron and desktop installation inspection. It does not install REA or modify the Sonoxo fork.

## Usage

Install REA from official upstream instructions with a supported Node.js version. Use a local GPT-Doug checkout with the gpt-chaos command available.

Plan only (no actual inspections):

    mkdir -p "$HOME/rea-evidence"
    gpt-chaos rea --mode javascript --target "$HOME/projects/my-electron-app" --output "$HOME/rea-evidence"

Run operator-authorized static inspection:

    gpt-chaos rea --mode javascript --target "$HOME/projects/my-electron-app" --output "$HOME/rea-evidence" --workers 2 --execute --authorized

Use desktop mode for local installed application directories. You may repeat the target flag up to eight times.

## Boundaries

- Max four worker processes, eight sources, 600 seconds per process, 64 MiB of evidence per process; defaults 2 workers, 120 seconds, 16 MiB.
- Explicit existing absolute paths required. Refuses symlink entrypoints, target/output overlap and duplicate inputs.
- Plan-only mode produces no filesystem modifications. Execute mode requires affirmative authorized flag and passes through existing GPT-Doug AI kill-switch.
- Invokes only documented static workflows: analyze-javascript-application and inspect-desktop-application, through the local REA CLI.
- Private, fresh evidence directory contains SHA-256 verified JSON and manifest. Invalid JSON, error results, timeout, size overflow and denied scope become BLOCKED.
- This is local process concurrency, not remote model inference. No external discovery, installer, deployment, credential collection, self-propagation or publishing.
- The 14 local acceptance tests passed using mock REA. Live-provider/real REA and complete integration tests remain unverified.

## XUNIA Museum record

SONOXO_REA_KRAKEN_SWARM; category Software Research; layer GPT-Chaos; state PROTOTYPE; museum publication NOT PERFORMED. Only publish a redacted manifest following authorization.
