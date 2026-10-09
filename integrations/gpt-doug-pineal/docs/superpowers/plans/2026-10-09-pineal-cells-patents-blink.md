# PINEAL Cell Atlas + Patent Network Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend PINEAL with an honest educational cell atlas, an auditable patent-publication index that accepts authorized worldwide metadata, and a blinking Mac terminal cortex.

**Architecture:** New immutable biological metadata/simulator module and a separate patent validation/adapter module use the existing SQLite + authenticated HTTP service for persistence and discovery. The terminal UI is a pure read-only renderer layered on the existing dashboard. Network calls remain off by default and are bounded to an explicit known-ID EPO lookup.

**Tech Stack:** Python 3.10+, standard library, SQLite, unittest-compatible pytest, ANSI terminal, GitHub CI.

**Spec:** `docs/CELL_PATENT_NETWORK_SPEC.md`

## Global Constraints
- No biological creation, wet-lab protocols, embryo interventions, human brain access, or automatic third-party scraping.
- No claims of global index completeness; metadata != efficacy or patent freedom-to-operate.
- All local imports provenance tagged, validated, transactional, and audited. No credentials in database.
- EPO lookup only with `--online`, bounded response/timeout, no redirect to unapproved domain.
- Mac terminal TTY + piped output supported without paid external dependencies.

## Review Focus
- Conflicting publication IDs from different sources: reject atomically; test in Task 2.
- URL with untrusted fake subdomain or redirect: reject; test in Task 2 + 3.
- Oversized or malformed JSONL file: import writes nothing; test in Task 2.
- Empty/new database and non-TTY watch: honest counts, no remote claims, bounded frames; test in Task 4.
- Live EPO API malformed, failure or missing metadata: no DB writes and error; test in Task 3.

---

### Task 1: Read-only cell ontology and symbolic cell simulator
**Files:** Create `src/pineal/cells.py`; create `tests/test_cells.py`.
**Interfaces:** `list_cells() -> list[dict]`, `simulate(cell_id: str, steps: int) -> dict`.
- [x] Write failing tests for curated cell types, unknown types, parthenogenesis disclaimer, bounded deterministic symbolic steps.
- [x] Run `PYTHONPATH=src python3 -m pytest -q tests/test_cells.py` and verify missing import fails.
- [x] Implement immutable curated ontology and symbolic state engine, with no culture/genetic protocols.
- [x] Re-run targeted suite and baseline; green.
- [x] Commit.

### Task 2: Worldwide patent bibliographic index and local atomic ingest
**Files:** Create `src/pineal/patents.py`, `tests/test_patents.py`; modify `src/pineal/store.py`.
**Interfaces:** `validate_record(data: dict) -> dict`, `load_records(path: Path, limit: int=1000) -> list[dict]`, `PinealStore.import_patents(records: list[dict]) -> dict`, `PinealStore.search_patents(query: str, limit: int=20) -> list[dict]`, `PinealStore.patent_stats() -> dict`.
- [x] Tests: normalized ids, allowed source URL, malicious URL rejected, duplicate idempotency, atomic conflict rollback, bad-file no-op, bounded search, cited cell tags.
- [x] Run targeted tests RED.
- [x] Implement validation, bounded JSONL/CSV loading, SQLite schema and transactional inserts with existing audit chain.
- [x] Run targeted and full suite GREEN.
- [x] Commit.

### Task 3: Official sources and opt-in EP one-publication metadata adapter
**Files:** Modify `src/pineal/patents.py`; create `tests/test_patent_sources.py`.
**Interfaces:** `list_sources() -> list[dict]`, `fetch_ep_metadata(publication_id: str, *, opener=None, timeout: float=8) -> dict`.
- [x] Tests: all sources show restrictions; non-EP reject; simulated valid JSON metadata; redirect rejection, payload too large, no metadata, offline default.
- [x] Run targeted tests RED.
- [x] Implement EPO exact-host single-record HTTPS JSON metadata fetch with bounded payload; no arbitrary URLs, no background crawling.
- [x] Run targeted and full suite GREEN.
- [x] Commit.

### Task 4: Mac CLI blink and safe API/dashboard integration
**Files:** Modify `src/pineal/cli.py`, `src/pineal/dashboard.py`, `src/pineal/http_api.py`; create `src/pineal/blink.py`; create `tests/test_blink.py`; extend `tests/test_api.py`.
**Interfaces:** `render_blink(store: PinealStore, frame: int=0, color: bool=False) -> str`; `run_blink(...)->int`; CLI subcommands and read-only API.
- [x] Tests: CLI cells/patents; bounded non-TTY blink frames; index summary; bearer required for patent/cell API; existing dashboard still truthful.
- [x] Run targeted tests RED.
- [x] Implement minimal CLI, API, TTY, and display changes.
- [x] Run all tests GREEN; smoke Mac commands with `PYTHONPATH=src python -m pineal`.
- [x] Commit.

### Task 5: Docs, review, and GitHub synchronization
**Files:** Modify `README.md`, `pyproject.toml`, add `docs/PATENT_CONNECTORS.md` and GitHub CI workflow if needed.
- [x] Document scientific limits, legal data-source constraints, examples, installation, status, and source URLs.
- [x] Run full pytest, compileall, clean import/display smoke; make source ZIP.
- [x] Perform self review of diff, record limitations; commit.
- [x] Publish to an integration branch in `sonoxo/gpt-doug-llm` and open a non-merged PR; inspect GitHub CI status, never claim checks pass before completion.

## Execution evidence and rulings
- Baseline: 40/40 tests passed before this change.
- Task 1: 6 new cell tests red then green; baseline 46/46.
- Task 2: 12 patent tests red then green; 58/58.
- Task 3: 5 patent source tests red then green; 63/63; self-review adjusted redirect test to assert the actual `NoRedirect.redirect_request` contract.
- Task 4: CLI/API and non-TTY blink tests red then green; 69/69.
- Final self-review (no subagent reviewer available): tightened ISO date format, stopped over-limit JSONL decoding early, rejected empty credential URL userinfo, and connected citation matches into ontology/context retrieval. Corresponding regression tests observed red then green. 75/75 local tests passed.
- Ruling: initial EPO adapter does not claim verified live endpoint availability because the official service was inaccessible from execution environment; it fails closed and the only intended network operation requires `--online` and a known EP publication ID.
- Ruling: universal coverage is an extensible importer, not a complete worldwide mirror; ODP, WIPO and local office terms/credentials remain authoritative.
- GitHub CI deployment outcome is tracked separately from local execution evidence.
