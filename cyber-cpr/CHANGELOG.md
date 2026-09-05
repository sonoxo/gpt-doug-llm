# Changelog

All notable Cyber CPR changes are documented here.

## 0.1.0 — 2026-09-05

### Added
- Local-first defensive repository heartbeat for GitHub Actions.
- Multi-repository monitoring with a default 180-second pulse.
- Persistent local health state and recovery detection.
- Five-check `🔥 STREAK` milestone.
- Explicit allow-listed bounded repair hook, disabled unless configured.
- Portable installer and uninstaller for macOS/Linux.
- macOS LaunchAgent service installer for background monitoring.
- Release packaging with SHA-256 checksum generation.
- Dedicated GitHub Actions validation and release-artifact gate.

### Safety boundary
- No autonomous secret, credential, repository-permission, production-data, firewall, or private-runtime mutation.
- Repair commands must be explicit local allow-list entries and are verified on a later pulse.

### XUNIA convention
- GrimTheBuilder is the browser IDE at `https://orbit-code-studio.almighty-son-8109.chatgpt.site/`.
- `hello-world` and GitHub `grimthebuilder` folders remain workspace/export/integration artifacts only.
