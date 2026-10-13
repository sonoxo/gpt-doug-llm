# GPT-Doug Guardian — Autonomous Resilience Simulation

**Project owner attribution:** Douglas Montel Brown Jr.  
**Status:** working offline training and research prototype  
**Repository:** https://github.com/sonoxo/gpt-doug-llm  
**Release:** guardian-v1 · 2026-10-13

## Start the dashboard — free, offline

Open `guardian_ops/guardian-command.html` in a modern browser. The entire simulation runs in the page with no API keys, accounts, telemetry, trackers, servers, third-party JavaScript or permissions. If your browser blocks local file pages, use an operator-owned, local HTTP server:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8765/guardian_ops/guardian-command.html`. **Do not expose the server to a public interface.**

The controls support autonomous step/run, emergency stop, named human incident approvals, two-person rearm, synthetic incident injection, fleet telemetry, response matrix, audit timeline and exported JSON report.

## Run the Python simulation

From the extracted project directory:

```bash
python3 -m gpt_doug_guardian --steps 24 --out guardian-report.json
python3 -m unittest discover -s tests -p 'test_guardian.py' -v
```

No external pip packages are needed for the Python simulation or tests. Browser acceptance tests use optional Playwright and Chromium:

```bash
# Included in the downloadable ZIP bundle: python3 tests/test_dashboard.py
```

## System architecture

| Layer | Implementation | Purpose |
| --- | --- | --- |
| Guardian swarm | `gpt_doug_guardian/sim.py` | Deterministic, bounded task allocation with 10 role-diverse software agents |
| Biocomputer metaphor | Energy, heartbeat, quarantine | Simulated metabolism, immune checks and recovery; not living cells or biological computing hardware |
| Navigation | Bounded BFS grid | Obstacle avoidance and return-energy reservation, not physical robotics |
| Command plane | `guardian_ops/guardian-command.html` | Live SVG fleet map and operator controls; runs locally without connectivity |
| Memory | SHA-256 chain in Python events | Reproducible audit and integrity verification; JSON export |
| Governance | Operator authorization + stop latch | Two distinct operators required for simulated severity 4–5 incidents and emergency-stop reset |

The Python engine is the reference for safety invariants. The browser is an independent demonstration engine built on the same synthetic scenario and controls; they do **not** share live state or synchronize over the network. A generated browser report is not cryptographically signed. Do not represent either as validation of real robot operation.

## Safety invariants

- All world coordinates are abstract **26 × 16 integer training cells**, with no mapping to real-world locations or identities.
- This software has **no weapons, targeting, fire-control, physical-actuation, TAK/CoT transmission, drone-command, hardware serial, radio or external-network interface**.
- The fleet cannot self-replicate; node counts, incidents, time and event histories have bounded limits.
- Human approval is mandatory before the simulator dispatches rescue, communications or logistics scenarios; severity 4–5 requires distinct operator IDs. This demonstrates review gates but is not real identity verification; production use requires authenticated operator identity and independent authorization.
- The Python simulation cooperates with `GPT_DOUG_AI_BLOCK_ALL` and the `GPT_DOUG_AI_STOP_DIR/STOP` file used by the existing GPT-Doug project to fail closed, and has its own internal emergency stop state.
- The emergency-stop state in the browser persists across local page reloads via localStorage when supported. Its two-person rearm input **is a training exercise**, not multi-factor authentication or a deployable safety controller.
- Do not connect this proof of concept to operational DoD systems, TAK servers, physical robots, satellites, weapons, or protected infrastructure. Separate real-world safety engineering, authorization, testing, certification and review would be necessary.

## Validation completed

- 17 deterministic stdlib `unittest` checks passing: simulation-only, no real coordinates, fleet bounds, no weapon fields, human approvals, energy-safe pathing, incident capacity, replay, audit integrity, host kill switch and emergency stop.
- Playwright/Chromium end-to-end acceptance passing: dashboard render, SVG map, response and audit tabs, time advancement, human approval, dual control, emergency stop/rearm and local JSON export.

## Integrations with GPT-Doug ecosystem

This prototype is designed to live alongside existing `agents/synthetic_mission_sim.py`, `zyra_defense_simulator.py` and `ai_killswitch.py` in `sonoxo/gpt-doug-llm`. No operational TAK connection has been built. Integration into an actual shared orchestrator or packaged Python entrypoint is **future work**, subject to code review and tests.

## Use restrictions

**Training, disaster resilience, humanitarian logistics, defensive research and operator education only.** This project is not a combat robot army and does not authorize or enable lethal autonomous operations, coercive surveillance, or attacks against people or systems.
