# GPT-DOUG-LLM — Framework reliability upgrade (2026-11-06)

This change is a **reviewable reliability upgrade**, not a claim that every
repository, GitHub Actions workflow, package, or physical device is fully
updated. No paid APIs or cloud service credentials are required.

## Work completed in this change

- **Root cause:** the unified test workflow collected real PyTorch tests
  (`tests/test_delta.py`, `tests/test_gpt_doug_motion_one.py`) without
  installing PyTorch. It also requires Pillow and Safetensors for ML tests.
  Install CPU PyTorch from its official CPU wheel index before collecting tests;
  use the project's existing `[mlm]` extra for version-constrained model
  dependencies. Do not use GPU/CUDA wheels on the Linux CI runner.
- **Cross-module health matrix:** `gpt-doug-health` reports importability of
  the GPT-DOUG brain, agent system, model layer, guardians, hivemind, NXYZ cloud,
  qbio simulation and watchdog. Optional SKULL-LLM (PR #503), VA3LM (separate
  distribution), and PyTorch are clearly labeled optional.
- **Emergency stop:** read the operator-owned STOP state without changing it.
- **Ollama:** `--ollama` explicitly opts into querying the *local loopback*
  Ollama server. No internet probes, no redirect following, no API tokens.
  Without this flag the readiness test is entirely offline.
- **Versioned framework gate:** a free, read-only GitHub Actions job tests
  Python 3.11/3.12 installation and diagnostics. A weekly readiness check
  reports broken importability without executing agents.
- **Consistent licensing:** npm metadata and the lockfile now declare MIT,
  matching the repository LICENSE and Python package metadata.
- **npm vulnerability remediation:** pinned safe dependency floors through npm
  overrides and regenerated the lockfile with no install scripts. Confirmed
  `body-parser` **2.4.0** (GHSA-27r3-jxmh-p828) and `qs` **6.17.1**
  (GHSA-6pq8-jhm2-2vcw), with `npm ci` and `npm audit --audit-level=high`
  passing on the Node 22 runner. Existing root npm security CI remains the
  ongoing check; its suppression level was not weakened.

## Mac terminal commands

In a clean checkout after this branch merges to main, use a virtual
environment rather than overriding macOS/Homebrew's externally managed Python:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/gpt-doug-health
.venv/bin/gpt-doug-health --json --strict
.venv/bin/gpt-doug-health --ollama
```

Before merge, check out this feature branch separately. Do **not** replace
the existing working `~/gpt-doug-skull` installation without a deliberate
integration of PR #503; that SKULL branch is not yet merged into main.

What the states mean:

| Status | Meaning |
| --- | --- |
| IMPORTABLE | The module is discoverable in the current Python environment. This is not an inference, health, or hardware test. |
| MISSING | Python cannot locate the component module here. |
| STOPPED | The existing operator-owned AI emergency stop is engaged. |
| OFFLINE | An explicitly requested local Ollama probe could not reach a valid model list. |
| NOT_CHECKED | No local Ollama call was attempted. |
| CL1 / SKULL | Hardware connectivity is **not** claimed. The biochip visualization remains synthetic until physical hardware is separately integrated. |

The `--strict` exit code is 1 if any **required** component cannot be
imported; 0 otherwise. The emergency stop is deliberately not rearmed or
changed. Optional components do not fail the core gate.

## Framework-wide follow-up work (not performed in this PR)

- The repository has many independent services, CI workflows, and optional
  dependency groups; each requires its own functional tests before claiming
  full deployment readiness.
- The SKULL macOS terminal and desktop UI remain on PR #503 until reviewed,
  integrated, and retested against the updated main branch.
- The existing weekly `scripts/sonoxo_fleet_upgrader.py` is the read-only
  audit mechanism for other Sonoxo repositories. This PR does not mutate them.
- The broad unified CI suite must complete and pass after dependency repair.
  Failures *after* dependency installation must be diagnosed individually;
  the missing-PyTorch root cause does not establish the absence of all others.
- Vulnerability review, migrations and high-risk dependency major updates
  require separate evidence and rollout gates. Never use a global
  `pip --break-system-packages` workaround on macOS.
