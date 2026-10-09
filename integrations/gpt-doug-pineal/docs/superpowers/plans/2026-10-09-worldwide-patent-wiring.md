# Worldwide Patent Connectivity Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, using test-driven development.

**Goal:** Connect authorized patent publication APIs to GPT-Doug-PINEAL's local provenance index and Mac Terminal without presenting unverified sources as connected.

**Architecture:** A small bounded HTTPS adapter layer normalizes bibliographic metadata into the existing `validate_record` and `PinealStore.import_patents` transaction. Network operations are explicit, whitelisted, rate-bounded and testable with fake transports. Credential presence is distinct from a verified connection.

**Tech Stack:** Python 3.10+ standard library, pytest, SQLite, macOS ANSI terminal, Github Actions.

**Spec:** `docs/PATENT_CONNECTORS.md` (source constraints) and this plan. Current user-provided USPTO excerpt is an input for an optional local seed fixture, not evidence of functioning human cell creation.

## Global Constraints

- Never scrape public WIPO PATENTSCOPE or Google Patents search interfaces.
- Never send API credentials or source data to untrusted origins; never log secrets.
- Offline CLI and existing authenticated loopback HTTP routes must keep working.
- New connectors are opt-in (`--online`); no automatic broad download/crawl.
- Source provenance and atomic conflict handling are mandatory.
- Only authorized bibliographic metadata, no personal clinical or genetic data.

## Review Focus

- Credentials absent: fail before any network request and without exposing secret values.
- Untrusted redirect or larger-than-cap payload: reject before import.
- Wrong publication ID in provider response: never store under requested ID.
- Batch partially fails: no partial database writes.
- Offline status: never claim a verified live connection without a successful probe.

### Task 1: EPO OPS worldwide publication adapter

**Files:** `src/pineal/patent_connectors.py`, `tests/test_patent_connectors.py`
**Interfaces:** `fetch_ops_publication(publication_id, *, opener=None, environ=None, timeout=8) -> dict`; `patent_connection_status(environ=None) -> list[dict]`.

- [ ] Add failing tests for OAuth, exact XML metadata extraction, no credentials, wrong record ID, malicious redirects and oversized payloads.
- [ ] Run tests, observe specific failure.
- [ ] Implement bounded OAuth and publication biblio XML adapter.
- [ ] Run target tests and entire package suite.

### Task 2: PatentsView U.S. grant adapter

**Files:** `src/pineal/patent_connectors.py`, `tests/test_patent_connectors.py`
**Interfaces:** `fetch_patentsview_grant(publication_id, *, opener=None, environ=None, timeout=8) -> dict`; `fetch_patent(publication_id, *, source='auto', opener=None, environ=None, timeout=8) -> dict`.

- [ ] Add failing tests for exact grant lookup, wrong ID, a non-grant request, absent key, and source routing.
- [ ] Run tests, observe failure.
- [ ] Implement authenticated bounded provider adapter and routing.
- [ ] Run target tests and package suite.

### Task 3: CLI, local sync, status and terminal wiring

**Files:** `src/pineal/cli.py`, `src/pineal/patent_connectors.py`, `src/pineal/patents.py`, `src/pineal/blink.py`, `src/pineal/http_api.py`, `tests/test_cli_patent_network.py`.
**Interfaces:** `patents connect-status`; `patents fetch ID --source ... --online`; `patents sync FILE --online [--dry-run]`.

- [ ] Add failing tests for offline status, explicit online gate, idempotent import, bounded batch, dry run and existing UI compatibility.
- [ ] Run tests, observe failure.
- [ ] Implement CLI operations and honest dashboard/API source status.
- [ ] Run target tests and full suite.

### Task 4: Documentation and delivery

**Files:** `README.md`, `docs/PATENT_CONNECTORS.md`, `examples/patents/user-supplied-us-publication.jsonl`, `pyproject.toml`, `.github/workflows/pineal-patent-connectors.yml`.

- [ ] Document verified sources and required credentials, limitations and macOS one-command install.
- [ ] Test `python -m pytest -q` and CLI smoke on isolated PINEAL_HOME.
- [ ] Commit, publish to existing GitHub feature branch, update PR for review.

## Decision Log

- Worldwide coverage means interoperable normalized bibliographic publication IDs; it does not mean downloading every record or accessing restricted APIs without credentials.
- USPTO ODP remains credentialed export until an exact versioned publication endpoint/schema is verified; U.S. *grant* lookup is instead provided via PatentsView with a valid existing API key.
