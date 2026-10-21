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

## Global, offline evidence consolidation (no remote execution)

Copy each approved machine's complete private `rea-swarm-*` directory to a trusted verification workstation. The verifier uses relative evidence filenames, so bundles may be relocated without relying on source machine paths. Then run:

    gpt-chaos rea-verify --manifest "/absolute/path/to/site-A/manifest.json" --manifest "/absolute/path/to/site-B/manifest.json"

The resulting `SONOXO_REA_EVIDENCE_FEDERATION` report checks JSON schema, job state, SHA-256 and byte lengths, rejects evidence symlinks and filename traversal, and distinguishes VERIFIED, PARTIAL, and BLOCKED. Maximum: 32 manifests per invocation. There is no synchronization client, hosted coordinator, remote scanner, message bus or cloud deployment. An exported or forged manifest is **not authenticated** solely by its checksum; trusted origin and operator approval require separate controls. Do not publish private paths or application evidence to the XUNIA site.

## Verification gates

- Local integration tests: **22/22 passed** on a disposable mock REA executable and imported bundle fixtures. Real REA execution has not passed yet.
- Dedicated CI: `.github/workflows/rea-kraken-swarm.yml` runs Python 3.11–3.13 offline contract checks and CLI dry-run smoke without the REA npm package.
- Optional real-provider test: explicitly dispatch that workflow with `run_real_rea=true`; it installs official REA into an ephemeral GitHub runner and inspects only a harmless checked-in fixture. This is **not** a global production deployment.
- Independent shared-suite blocker: the optional PyTorch MLM test module was updated to skip test collection on runners without the `.[mlm]` extra; the specialized MLM training workflow still executes its real torch tests.
- Both general CI and the dedicated REA gate must pass, and the real fixture test must produce an inspected evidence bundle, before release readiness can be claimed.
