# ECO-SHAGGOTH-CL1 — Full Interactive Spatial Terminal

**Not a picture or a web page.** This is a real keyboard/mouse-interactive, full-screen, 3D-projected terminal topology of the GPT-DOUG ecosystem. It runs in macOS Terminal/iTerm2 using Python's standard-library curses. It never calls paid APIs or starts autonomous agents.

## Launch

Use a new isolated checkout, because earlier branch switches in your existing CL1 checkout were blocked by untracked Kraken Shield files:

    cd "$HOME"
    git clone --depth 1 --single-branch \
      -b feat/eco-shaggoth-cl1-spatial-terminal-20261114 \
      https://github.com/sonoxo/gpt-doug-llm.git \
      "$HOME/eco-shaggoth-cl1"
    cd "$HOME/eco-shaggoth-cl1"
    bash scripts/eco-shaggoth-cl1

To launch it again later:

    cd ~/eco-shaggoth-cl1 && bash scripts/eco-shaggoth-cl1

This standalone visual terminal does **not** need Ollama, an API key, npm, pip or a web browser; model and service status indicators reflect any already running local services. You can start your existing CL1 web server in another Terminal tab independently.

## Terminal controls

| Key | What happens |
| --- | --- |
| Left / Right, A / D | Rotate the 3D spatial ecosystem |
| Up / Down, W / S | Tilt the view |
| H / J / K / L | Pan viewport left/down/up/right |
| + / - | Zoom in/out |
| Tab / Shift+Tab | Select next/previous visible entity |
| Enter | Center selected entity |
| N / B | Next/previous ontology layer |
| / | Find an entity by name (e.g. Glass Onion, Ollama) |
| R | Recheck locally listening TCP ports |
| V | Toggle animated organic Shaggoth / edge flow |
| G | Toggle star grid |
| T | Toggle node labels |
| F | Reset camera and layer |
| ? | Interactive help overlay |
| Mouse click | Select nearby node (terminal permitting) |
| Q | Exit without changing services |

For best results enlarge your Terminal to **at least 110 columns x 34 rows** (minimum 89x23) and use a font with Unicode glyph support. No Terminal color/font changes are installed or modified.

## What appears

- **Center:** living organic ECO-SHAGGOTH construct, actual 3D nodes and relational edges, animated flows; camera yaw, pitch, zoom and pan change the projection.
- **Left panel:** ontology layer filter and loopback status indicators.
- **Right panel:** node inspector with type, source file provenance, local status, description and architectural relationships.
- **Bottom controls:** interactive instructions and viewport telemetry.

There are 18 mapped nodes spanning core inference, XUNIA, Kraken Shield, Glass Onion, ZYRA, bounded swarm, North Star, Jukebox, bank-deny policy, sealed vault, NXYZ, Greenhouse, optional Foundry adapter, audit and Shaggoth Nexus. Edges are *architectural relations*, not verified live network calls.

## Truth and safety boundaries

- **LISTENING** means that a TCP connection to 127.0.0.1:port succeeded. It does not establish service identity, valid authentication, secure configuration or a running model.
- **MAPPED** is only a repository ontology label, never an active runtime claim.
- **CODE** means a local policy source file exists, not that protection is enforced universally.
- **BANK DENY** and **VAULT SEALED** are policy designations, not connectivity or third-party bank account protection.
- The visualization never inspects private banking accounts or credentials, unlocks the Glass Onion vault, starts services, sends financial actions, provisions cloud resources or changes Git.
- Socket probes are bounded short connections to **127.0.0.1 only** on ports 11434, 8787, 8844 and 8791; no HTTP requests, telemetry uploads, or external connections.

## Headless snapshots / ontology export

    bash scripts/eco-shaggoth-cl1 --snapshot --offline
    bash scripts/eco-shaggoth-cl1 --json

The JSON export is printed to stdout, so it can be saved or piped elsewhere if desired. It contains only the topology, no secrets.

## Testing

    python3 -m unittest discover -s tests -p 'test_eco_shaggoth_spatial.py' -v
    python3 -m compileall -q scripts/eco_shaggoth_cl1.py
    bash -n scripts/eco-shaggoth-cl1

The feature PR is stacked on GLASS ONION activation PR #524, which is itself stacked on the CL1 / Kraken / Glass Onion chain. A CI pass confirms software checks only; the final macOS interactive appearance needs a real Terminal run.
