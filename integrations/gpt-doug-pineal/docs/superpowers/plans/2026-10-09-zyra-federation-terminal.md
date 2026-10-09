# ZYRA Federation Terminal Cortex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver a privacy-preserving terminal visualization and ingestion layer for ZYRA-connected GPT-Doug infrastructure, with provider templates and defensive boundaries.

**Architecture:** An offline, immutable provider registry and per-sector policy validate numeric observations before storing them in PINEAL's existing SQLite store. A read-only, ANSI-compatible terminal dashboard renders authenticated local state and clearly marked synthetic examples without invoking third-party systems.

**Tech Stack:** Python >=3.10, sqlite3, argparse, standard library, pytest.

**Spec:** `docs/FEDERATION_SPEC.md`

## Global Constraints
- Never imply live access to named companies, defense systems, or markets.
- Local-only, no hardware actuation, no collection of personal brain data.
- Defense node only synthetic, aggregate defensive readiness and simulated SI health.
- All accepted observations are finite, source-attributed, audited, and structured.
- Use no non-standard runtime dependencies; preserve existing CLI/API behavior.

## Review Focus
- Unknown node / malformed metric: fail closed; test in Task 1.
- Credential-like input or NaN/Infinity: reject without writes; test in Task 1.
- Non-synthetic defense or neuro raw data: reject; test in Task 1.
- Federation API unauthenticated request: return HTTP 401; test in Task 2.
- Non-TTY and non-ANSI terminal output: no crashes or stray screen clearing; test in Task 3.

---

### Task 1: Registry and policy gate

**Files:** Create `src/pineal/federation.py`; test `tests/test_federation.py`.

**Interfaces:** `list_nodes() -> list[dict]` enumerates built-in sectors with `connected=False` and `status='not-connected'`; `validate_observation(node, metric, value, unit, source, synthetic=False, classification='PUBLIC') -> dict` returns a vetted data record; rejects unknown nodes, non-finite values, credentials, unsafe content and restricted categories.

- [x] Step 1: Write tests for the registry, allowed aggregate metrics and prohibited credential, biometric and weapon-system payloads.
- [x] Step 2: Run `pytest -q tests/test_federation.py` and confirm RED for missing module.
- [x] Step 3: Add immutable node definitions and explicit deny-by-default policy to `federation.py`.
- [x] Step 4: Run tests and confirm GREEN.
- [x] Step 5: Commit registry/policy/tests.

### Task 2: Persistence and authenticated introspection

**Files:** Modify `src/pineal/store.py`, `src/pineal/http_api.py`; test `tests/test_federation_store.py` and `tests/test_api.py`.

**Interfaces:** `PinealStore.record_observation(**fields)` inserts validated observations into new `federation_observations` table in one audit transaction; `PinealStore.list_observations(node=None, limit=100)` returns latest data; `GET /v1/federation` returns registry, counts and latest samples to authenticated caller.

- [x] Step 1: Write tests for persistence, audit, unconnected status, malformed input and HTTP authentication.
- [x] Step 2: Run tests and confirm RED for new methods/route.
- [x] Step 3: Implement add-on schema/methods and authenticated read-only route.
- [x] Step 4: Run tests and confirm GREEN; run existing suite.
- [x] Step 5: Commit persistence/API/tests.

### Task 3: ANSI visual cortex and CLI

**Files:** Create `src/pineal/dashboard.py`; modify `src/pineal/cli.py`; test `tests/test_dashboard.py`.

**Interfaces:** `render_dashboard(store, demo=False, color=False, width=100) -> str` displays node grid, metric bars/trends, Kraken advisories, shields and audit. `run_dashboard(store, demo=False, watch=False, interval=2.0, frames=None, color=None, stream=None) -> int` renders snapshots. CLI adds `federation`, `observe`, `dashboard` with documented flags; no automatic remote connections.

- [x] Step 1: Write tests for local-only dashboard, labeled demo, non-TTY rendering and CLI observation.
- [x] Step 2: Run tests and confirm RED for missing dashboard/CLI.
- [x] Step 3: Implement dashboard/CLI and safe bounded watch mode.
- [x] Step 4: Run tests and confirm GREEN; run entire suite.
- [x] Step 5: Commit dashboard/CLI/tests.

### Task 4: Documentation, packaging and CI proof

**Files:** Modify `README.md`, `pyproject.toml`; create `docs/FEDERATION_ARCHITECTURE.md`, update `examples` if useful.

**Interfaces:** Install from GitHub `#subdirectory=integrations/gpt-doug-pineal`, `pineal dashboard --demo --watch`, and safe `pineal observe` documented. Preserve local offline behavior and attach logs for tests.

- [x] Step 1: Confirm CLI package entrypoint can be installed in clean venv.
- [x] Step 2: Add documentation explicitly separating simulated vs user-imported vs authorized connected feeds.
- [x] Step 3: Run full pytest, demo render, lint/compile, package smoke test.
- [x] Step 4: Commit docs/metadata.
- [ ] Step 5: Sync files to GitHub integration branch; note new commit and workflow status.
