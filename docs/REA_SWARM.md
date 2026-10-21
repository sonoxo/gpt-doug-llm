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
- The mock-boundary and federation tests passed. The real upstream REA 6.7.0 synthetic-fixture smoke passed in GitHub CI; real third-party desktop application coverage, binary provider support, and production deployment remain unverified.

## XUNIA Museum record

SONOXO_REA_KRAKEN_SWARM; category Software Research; layer GPT-Chaos; state PROTOTYPE; museum publication NOT PERFORMED. Only publish a redacted manifest following authorization.

## Global, offline evidence consolidation (no remote execution)

Copy each approved machine's complete private `rea-swarm-*` directory to a trusted verification workstation. The verifier uses relative evidence filenames, so bundles may be relocated without relying on source machine paths. Then run:

    gpt-chaos rea-verify --manifest "/absolute/path/to/site-A/manifest.json" --manifest "/absolute/path/to/site-B/manifest.json"

The resulting `SONOXO_REA_EVIDENCE_FEDERATION` report checks JSON schema, job state, SHA-256 and byte lengths, rejects evidence symlinks and filename traversal, and distinguishes VERIFIED, PARTIAL, and BLOCKED. Maximum: 32 manifests per invocation. There is no synchronization client, hosted coordinator, remote scanner, message bus or cloud deployment. An exported or forged manifest is **not authenticated** solely by its checksum; trusted origin and operator approval require separate controls. Do not publish private paths or application evidence to the XUNIA site.

## Verification gates

- Local integration tests: **22/22 passed** on a disposable mock REA executable and imported bundle fixtures. A separate **real REA 6.7.0 smoke test passed** against the harmless committed fixture in a disposable GitHub runner. This does not prove universal application compatibility.
- Dedicated CI: `.github/workflows/rea-kraken-swarm.yml` runs Python 3.11–3.13 Linux and Python 3.12 macOS offline contract checks and CLI dry-run smoke without the REA npm package. The real fixture job pins `rea-agents@6.7.0`.
- Real-provider test: executes on trusted in-repository PRs, or by explicit workflow dispatch with `run_real_rea=true`. It installs official REA into an ephemeral GitHub runner and inspects only a harmless checked-in fixture. Successful test evidence: https://github.com/sonoxo/gpt-doug-llm/actions/runs/39689543406. This is **not** a global production deployment.
- Independent shared-suite blocker: the optional PyTorch MLM test module was updated to skip test collection on runners without the `.[mlm]` extra; the specialized MLM training workflow still executes its real torch tests.
- A reviewed merge and subsequent authorized site deployment are still required; CI passing does not mean the global fleet or public site has been deployed.

## XUNIA browser evidence console

The static, mobile-responsive site source is at `docs/rea-kraken/`. After the PR is reviewed, merged, and GitHub Pages publishes the deployment, the intended route is `https://xunia.org/rea-kraken/`. Until publication is verified, that address must **not** be reported as live.

The viewer accepts a single selected `manifest.json` together with its numbered `01.json` / `02.json` evidence files; it verifies their byte lengths and SHA-256 digests using browser Web Crypto without uploading them. Its demo generates purely synthetic evidence inside the browser. Loading different bundles one at a time creates a session-only local history, not a remote evidence repository. The site has `connect-src 'none'` content-security policy, and the JavaScript uses no remote API requests. Do not confuse browser evidence verification with installed REA execution, producer authentication, or operational deployment.

The XUNIA Pages CI workflow checks the HTML, JavaScript syntax, four Node verification tests, and static HTTP route before the site can publish.

## Verified cross-repository security dependency

The GPT-Doug Full Completion workflow checks out `sonoxo/zyra@main` and runs a high-severity npm audit. On October 21, 2026, Vite 7.3.6 caused that external audit to fail. The corrected ZYRA dependency (Vite 7.3.7, GitHub advisory GHSA-587h-7wmj-h5pm) passed its test, build, audit, quality and CodeQL gates in [ZYRA PR #104](https://github.com/sonoxo/zyra/pull/104). The patch was merged to `sonoxo/zyra` as `f7b059b0d58257ab94b6a0c0f4c232a89ec0def3`.

A fresh GPT-Doug CI run is still necessary because older REA PR checks read the vulnerable previous version of ZYRA's `main` branch. This dependency patch does not add runtime authority or distributed execution.
