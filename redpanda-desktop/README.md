# GPT-REDPANDA DESKTOP / MOBILE

USB-resident local-first assistant node for the GPT-DOUG-LLM ecosystem.

## What it does

- Keeps GPT-REDPANDA runtime state, memory, logs, and terminal event metadata on the USB node.
- Runs as a macOS LaunchAgent while the USB is mounted.
- Watches the terminal workflow without keylogging: it records only command exit status and current working directory.
- Automatically invokes `cyber-cpr check ... --repair` after failed terminal exits and on a 180-second heartbeat.
- Cyber CPR repair remains bounded: only explicitly enabled allow-listed commands in the USB `cyber-cpr-config.json` can execute.
- Serves a token-protected local web portal for desktop.
- Optional `redpanda-node lan` mode exposes the same portal to a phone on the same LAN.
- Optional local LLM chat uses the existing OpenAI-compatible llama.cpp endpoint at `http://127.0.0.1:9931/v1`.
- No paid API is required.

## Install to an already-mounted USB

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop/install.sh) auto
```

If more than one external volume is mounted, specify the target:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop/install.sh) "/Volumes/YOUR_USB"
```

## Commands

```bash
redpanda-node open
redpanda-node status
redpanda-node cpr
redpanda-node run
redpanda-node lan
```

`redpanda-node lan` binds to the LAN and prints a token-protected mobile URL. The default LaunchAgent binds to localhost only.

## USB layout

```text
<USB>/
├── .gpt-redpanda-node
├── GPT-REDPANDA/
│   ├── redpanda_agent.py
│   ├── redpanda-node
│   └── redpanda-zsh-hook.zsh
└── .redpanda/
    ├── cyber-cpr-config.json
    ├── events/terminal-events.tsv
    ├── logs/
    ├── memory/
    ├── portal-token
    └── status.json
```

A tiny host bootstrap lives in `~/.local/bin/redpanda-node` so macOS can rediscover the USB node. The substantive runtime and persistent state live on the USB.

## Terminal privacy

The zsh hook does **not** capture commands, keystrokes, arguments, passwords, or terminal output. Each event contains only:

```text
epoch    exit_status    current_working_directory
```

A non-zero exit can trigger a Cyber CPR health check without collecting the command that failed.

## Repair policy

The default USB config is:

```json
{
  "repairs": []
}
```

This means GPT-REDPANDA automatically detects and runs health checks, but no arbitrary local repair command is allowed. Add only explicit, reversible, repository-scoped repair rules that Cyber CPR already supports.
