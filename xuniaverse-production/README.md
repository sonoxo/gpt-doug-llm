# xuniaverse-production

A minimal, verified slice of the larger Xuniaverse ecosystem plan (Doug Blueprint): a
task-queue daemon that dispatches prompts to the `doug` Claude Code agent, gated by a
`zyra_guard` safety layer, with a thin web UI and persistent task-history context.

This is intentionally a small real increment, not the full ecosystem diagram (no
Google Cloud, Codex orchestration, or frontend IDE here — those are still unbuilt).

## Contents

- `xuni-workers/agent-daemon.py` — polls `xuni-workers/tasks/*.json`, runs each through
  `zyra_guard`, dispatches allowed tasks to `claude -p --agent doug`, writes results to
  `xuni-workers/results/`, and appends completed tasks to `xuni-workers/live/context.jsonl`
  so later tasks get real continuity.
- `xuni-workers/zyra_guard.py` — pre-flight safety gate: blocks destructive commands
  (rm -rf, force-push, DROP TABLE, permission-bypass flags, remote-exec pipelines),
  oversized prompts, and several obfuscation channels (whitespace variants, shell
  variable substitution, semantic/synonym phrasing, chained base64, hex, ROT13,
  quoted-string concatenation). Logs every decision to `xuni-workers/live/zyra.log`.
- `xuni-workers/web_ui.py` — stdlib-only HTTP server (`:8765`) to submit a prompt and
  poll for its result through the same task-file contract the daemon uses.
- `.claude/agents/doug.md`, `coder.md`, `tester.md` — the agent definitions the daemon
  dispatches to.
- `launchd/*.plist` — macOS launchd unit files that supervise the daemon and web UI as
  persistent background services (`~/Library/LaunchAgents/`).

## Known gaps (honest, not rounded up)

Zyra is a keyword/decode/pattern gate, not a sandbox — it doesn't catch Unicode
homoglyphs or arbitrary custom ciphers. The web UI has no auth. The daemon processes
tasks serially (no worker pool). None of the Google Cloud, Codex orchestration, or
product-engine layers from the wider ecosystem diagram exist yet.
