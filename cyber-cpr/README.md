# 🚑 Cyber CPR

**Detect. Stabilize. Repair. Verify. Revive.**

Cyber CPR is a local-first defensive DevSecOps utility for GitHub repository health and bounded recovery. It watches GitHub Actions, records a persistent heartbeat, identifies recovery transitions, and can run only explicitly enabled local repair commands.

**Current release: `v0.1.0`**

> Cyber CPR is defensive software. It does not automatically change secrets, repository permissions, production credentials, firewall policy, production data, or private infrastructure.

## Release capabilities

- ✅ GitHub Actions workflow-health monitoring through authenticated `gh`
- 🫀 one-shot checks and continuous 3-minute pulse
- 🔥 five-consecutive-healthy-check streaks
- 🚀 unhealthy → healthy recovery detection
- 🧠 persistent state in `~/.cyber-cpr/state.json`
- 🔧 explicitly allow-listed bounded local repair hook, off by default
- 🍎 optional macOS LaunchAgent for start-at-login/background operation
- 📦 deterministic `.tar.gz` release packaging
- 🔐 SHA-256 release checksums
- 🧪 dedicated Cyber CPR validation/package CI gate
- 🛡️ documented security and authorization boundary

## Requirements

- macOS or Linux
- Python 3.10+
- GitHub CLI (`gh`) authenticated for repositories you are authorized to inspect

## Install from source

```bash
git clone https://github.com/sonoxo/gpt-doug-llm.git
cd gpt-doug-llm/cyber-cpr
bash install.sh
```

Verify:

```bash
cyber-cpr check sonoxo/gpt-doug-llm
```

## Run Cyber CPR

One check:

```bash
cyber-cpr check sonoxo/xuniahub sonoxo/gpt-doug-llm
```

Continuous three-minute pulse:

```bash
cyber-cpr watch sonoxo/xuniahub sonoxo/gpt-doug-llm --interval 180
```

Status language:

```text
✅ HEALTHY       latest relevant completed runs are successful
❌ ATTENTION     one or more latest workflow states failed
⏳ PENDING       a latest workflow is queued/in progress
🚀 RECOVERY      previous pulse unhealthy, current pulse healthy
🔥 STREAK x5     five consecutive healthy pulses
```

## macOS: run automatically at login

Install the CLI first, then from this folder run:

```bash
bash install-service.sh sonoxo/xuniahub sonoxo/gpt-doug-llm
```

The LaunchAgent runs Cyber CPR every 180 seconds and restarts if the watcher exits. Logs are stored under `~/.cyber-cpr/`.

Remove only the background service:

```bash
bash uninstall-service.sh
```

## Build the distributable release

```bash
bash release.sh
```

Output:

```text
dist/cyber-cpr-0.1.0.tar.gz
dist/cyber-cpr-0.1.0.tar.gz.sha256
```

The dedicated **Cyber CPR** GitHub Actions workflow also builds and uploads these files as a downloadable workflow artifact after validated changes.

## Bounded repair

Cyber CPR follows:

```text
DETECT → CLASSIFY → CONTAIN → BOUNDED REPAIR → VERIFY → REPORT
```

Automatic repair is deliberately constrained. A repair must be explicitly configured in `config.json`, match an exact workflow name, run as an exact command, and execute inside an explicit local Git repository working tree. Unknown failures are reported instead of guessed at.

Example:

```bash
cp config.example.json config.json
cyber-cpr check owner/repo --repair --config config.json
```

Cyber CPR must **not** automatically mutate secrets or credentials, GitHub/Vercel/cloud permissions, branch protection, production databases or user data, firewall/authentication policy, or unrelated application logic.

## GrimTheBuilder / XUNIA convention

For XUNIA ecosystem checks, GrimTheBuilder means the browser IDE/program hosted at:

`https://orbit-code-studio.almighty-son-8109.chatgpt.site/`

The `hello-world` project and GitHub `grimthebuilder` folders are workspace/export/integration artifacts only, never the GrimTheBuilder application itself.

## Files

- `cyber_cpr.py` — engine/CLI
- `install.sh` / `uninstall.sh` — user-local CLI installation
- `install-service.sh` / `uninstall-service.sh` — macOS background pulse
- `config.example.json` — bounded-repair policy example
- `release.sh` — release archive/checksum builder
- `VERSION` — release version
- `CHANGELOG.md` — release history
- `SECURITY.md` — security boundary
- `LICENSE` — MIT license

## Uninstall

```bash
bash uninstall-service.sh  # macOS service, if installed
bash uninstall.sh
```

State can be removed separately:

```bash
rm -rf ~/.cyber-cpr
```

## License

MIT. Use only on repositories and systems you own or are authorized to administer.
