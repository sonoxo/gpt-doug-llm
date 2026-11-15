# CL1-AURA — Clickable ECO-SHAGGOTH Terminal and Local Spatial Window

**AURA is the actual input/control layer for the ECO-SHAGGOTH topology.**
It adds native mouse reporting to the existing curses spatial terminal,
and provides a zero-dependency localhost browser fallback when a terminal
emulator withholds mouse events. Both modes are **read-only**.

## One-command install-free launch on Mac

Use a separate folder to avoid untracked Kraken files in previous CL1 checkouts:

    cd "$HOME"
    git clone --depth 1 --single-branch \
      -b feat/cl1-aura-clickable-spatial-20261114 \
      https://github.com/sonoxo/gpt-doug-llm.git "$HOME/cl1-aura"
    cd "$HOME/cl1-aura"
    bash scripts/cl1-aura

If this folder already exists, don't clone over it; use:

    cd ~/cl1-aura && git pull --ff-only && bash scripts/cl1-aura

**Terminal.app:** If clicks select text instead of selecting nodes, choose
**View > Allow Mouse Reporting** in macOS Terminal. In iTerm2, enable
**Report mouse clicks & drags** and, for scroll zoom, mouse wheel reporting.
AURA requests standard curses events and xterm SGR-1006/1002 reports.
A terminal's preferences can still block mouse forwarding.

## Guaranteed clickable local fallback

If terminal mouse tracking is disabled or unsupported, use the local spatial
browser window (still launched from Terminal, no paid services or packages):

    cd ~/cl1-aura && bash scripts/cl1-aura --web

Open **http://127.0.0.1:8866/**. The native browser pointer controls operate
even when Terminal.app cannot forward mouse events. Leave the hosting Terminal
window running. Port 8866 is separate from GPT-DOUG:8787, Ollama:11434, and
ZYRA Jukebox:8844, so it does not interrupt those servers.

## Mouse, touchpad and keyboard actions

| Control | Effect |
| --- | --- |
| Click a spatial node or its label | Select node and show provenance/details |
| Click an ontology layer in left panel | Filter spatial nodes by layer |
| Click a linked entity in inspector | Jump to connected node |
| Click a local telemetry indicator | Inspect that mapped service |
| Click on-screen orbit/zoom/scan buttons | Operate the viewport |
| Click and drag in spatial field | Rotate camera yaw/pitch |
| Scroll mouse wheel / touchpad | Zoom (when forwarded by terminal) |
| Arrow keys / WASD | Rotate and tilt |
| H J K L | Pan viewport |
| Tab | Select next node |
| / | Find node by name |
| N/B | Cycle layers |
| R | Scan loopback TCP only |
| Q | Quit without changing any service |

The optional local-browser spatial view supports the same mouse interactions,
with native clickable DOM controls and a rendered Canvas graph.

## Engineering and security boundaries

- Terminal input implementation: \`scripts/cl1_aura_mouse.py\` provides
  pure hit tests and SGR-1006 parser, while \`eco_shaggoth_cl1.py\` handles
  curses buttons/drag/wheel and resets mouse reporting on exit.
- Browser fallback: \`scripts/cl1_aura_web.py\` exposes only static assets,
  \`/api/topology\` (static public architectural graph) and
  \`/api/status\` (loopback TCP probe results); it binds **127.0.0.1 only**,
  denies requests with non-loopback Host headers, and has no POST endpoint.
  No remote scripts or third-party fonts are loaded.
- No bank connections, payouts, music uploads, passwords, private vault unlock,
  cloud model calls, shell execution, Git changes or agent orchestration.
- A process marked **LISTENING** only accepts a loopback TCP connection;
  this is not proof of authentication, process identity or verified security.
- This is a clickable **architectural topology**, not a full digital twin or
  interactive shell-command execution system.

## Run tests

    python3 -m unittest discover -s tests -p 'test_cl1_aura_click.py' -v
    python3 -m unittest discover -s tests -p 'test_cl1_aura_web.py' -v
    python3 -m unittest discover -s tests -p 'test_eco_shaggoth_spatial.py' -v
    node --check apps/cl1-aura/aura.js
    bash -n scripts/cl1-aura

CI tests pure click coordinate mappings, raw SGR reports, simulated curses
clicks, local HTTP security and browser syntax on Python 3.11/3.12 and Node 24.
CI does not prove a user's specific terminal settings are enabled.

## Development status

Feature PR stacked on ECO-SHAGGOTH PR #525, which itself depends on the
unmerged Glass Onion and CL1 branches. It is **not merged into main** by this
change and does not start any processes on the user's Mac remotely.
