# GPT-Doug Warfighter Research Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable, local-only, synthetic Warfighter support ontology with deterministic simulation, exact-math verification, manual review, and research-only publication compatible with GPT-Doug, PINEAL, and ZYRA.

**Architecture:** Keep ZYRA_MSS_V1 unchanged; build a separate typed WARFIGHTER_RESEARCH_V1 graph, offline research engines, immutable run envelopes, SQLite review journal and a derived approved-finding overlay. Verification does not imply real-world readiness, and approval permits research publication only. No simulator ever dispatches tasks or calls external systems.

**Tech Stack:** Python >=3.9; stdlib json, pathlib, hashlib, sqlite3, fractions, unittest, argparse. Reuse research_lab.bio_hilbert and research_lab.multidimensional. Optional PINEAL package for explicitly requested projection; no cloud, GPU, Blender, or paid tokens required.

**Spec:** `docs/superpowers/specs/2026-10-12-quantum-warfighter-ontology-design.md`; canonical public design reference `docs/WARFIGHTER_RESEARCH_ONTOLOGY.md`.

## Global Constraints

- Canonical `safety-shield/ontology/zyra-mss-v1.json` remains unmodified. All new findings carry `authority=RESEARCH_ONLY` even after review.
- The existing PINEAL `warfighter-defense-si` accepts only SYNTHETIC records with allowlisted metrics: `patch_compliance_pct`, `training_readiness_pct`, `sensor_health_pct`, `simulation_alerts`, `zero_trust_coverage_pct`.
- Never access classified, CUI, export-controlled, personal, troop-position, targeting, weapons, or actual operational data.
- Do not call `workers.xqe.run`, `workers.xqe.verify`, `ontology.submit_task_action`, network clients, scanners, actuators, or model-provider APIs.
- Max synthetic scenario file 64 KiB; output envelope 1 MiB; graph 100 objects/500 links; baseline local concurrency 1; no new daemon.
- Preserve Bio-Hilbert's <=128 modes and <=8 steps and multidimensional exact-linear <=6 dimension ceiling without modifying existing math engines.
- Do not conflate a mathematically replayable certificate, a human-reviewed research publication, or real-world operational validation.
- Every persisted record has version, source_kind, classification, synthetic flag, provenance, timestamp, scope, SHA-256 digest, and current research-only status.
- TDD each task (write test, run RED, implement, run GREEN, commit) and run existing regressions before PR.
- Tests use `python3 -m unittest`; optional existing pytest suites must run when pytest is available.

## Review Focus

1. **Symlink/path escape** must be rejected on fixture ingest and workspace creation (Tasks 2 and 6; test files `test_fixtures.py`, `test_journal.py`).
2. **False PUBLIC data or a password field** must fail closed before any simulation (Tasks 1-2; `test_schema.py`, `test_fixtures.py`).
3. **Replayed-but-inconclusive mathematics** must never be labeled PROVED or operationally ready (Tasks 4-5; `test_math_adapter.py` and `test_verify.py`).
4. **Forged APPROVED field, changed digest, duplicate or revoked publication** must never reach active research queries (Tasks 6-7; `test_journal.py`, `test_publication.py`).
5. **Existing XQE task dispatch or implicit PINEAL writes** must not be invoked in simulate, verify or status commands (Tasks 8-9; `test_pineal_projection.py`, `test_cli_e2e.py`).

---

## File Map

| Path | Single responsibility |
| --- | --- |
| `safety-shield/ontology/warfighter-research-v1.json` | Versioned type/link definitions, research-only invariants |
| `research_lab/warfighter/__init__.py` | Safe import boundary |
| `research_lab/warfighter/schema.py` | Instance, relation, scope, and classification validator |
| `research_lab/warfighter/fixtures.py` | Bounded local data ingest + canonical digests |
| `research_lab/warfighter/baseline.py` | Synthetic aggregate what-if simulation |
| `research_lab/warfighter/hilbert_adapter.py` | Read-only exact mathematics adapters |
| `research_lab/warfighter/artifact.py` | Immutable run envelope creation |
| `research_lab/warfighter/verify.py` | Independent replay/checksum/certificate verification |
| `research_lab/warfighter/journal.py` | Quarantine + review-event SQLite journal |
| `research_lab/warfighter/publication.py` | Research overlay and revocation |
| `research_lab/warfighter/pineal_projection.py` | Optional approved namespace write/reconciliation |
| `research_lab/warfighter/cli.py` | User-controlled local terminal commands |
| `research_lab/warfighter/examples/synthetic_training_defense.json` | Deterministic golden exercise |
| `research_lab/warfighter/tests/test_*.py` | Focused negative/positive regression tests |
| `scripts/doug-max` | Guarded CLI dispatch, no bypass |
| `docs/WARFIGHTER_RESEARCH_ONTOLOGY.md` and `docs/WARFIGHTER_RESEARCH_CLI.md` | Truthful public implemented vs planned status |

### Task 1: Canonical Extension Schema, Typed Graph

**Files:** Create `safety-shield/ontology/warfighter-research-v1.json`, `research_lab/warfighter/__init__.py`, `research_lab/warfighter/schema.py`, `research_lab/warfighter/tests/test_schema.py`.

**Interfaces:** `load_schema(path: Path | None = None) -> dict[str, Any]`, `validate_record(record: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]`, `validate_graph(nodes: list[dict], edges: list[dict], schema: Mapping[str, Any]) -> None`.

- [ ] **Step 1: Write failing tests** asserting schema ontology_id `WARFIGHTER_RESEARCH_V1`, authority `RESEARCH_ONLY`, all 21 new object types and 15 directed link types exactly matching Spec ``5.2-5.3`; `ResearchEvidence --SUPPORTED_BY--> MathCertificate` works. Reject wrong types, missing mandatory fields, duplicate IDs, 101 nodes, 501 links, self-review link, unknown fields including `api_key` or `password`, and nonsynthetic/public Warfighter claims.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_schema -v`. Expected RED: module/schema absent.
- [ ] **Step 3: Implement** the three named APIs. Validate each node's id, schema_version, type, source_kind, classification, synthetic, created_at, provenance, source_refs, evidence_status, confidence_scope and record_sha256; validate link endpoints and graph bound before any storage; never eval embedded text or redefine base ZYRA types.
- [ ] **Step 4: Run** same focused command. Expected GREEN.
- [ ] **Step 5: Commit** `git add safety-shield/ontology/warfighter-research-v1.json research_lab/warfighter && git commit -m "feat(warfighter): define isolated typed research schema"`. Stage only Task 1 files.

### Task 2: Synthetic Fixture Intake and Provenance

**Files:** Create `research_lab/warfighter/fixtures.py`, `research_lab/warfighter/examples/synthetic_training_defense.json`, `research_lab/warfighter/tests/test_fixtures.py`.

**Interfaces:** `canonical_json(value: Any) -> bytes` with sorted keys, fixed separators, ensure_ascii=True, allow_nan=False; `digest(value: Any) -> str` using SHA-256; `validate_scenario(payload: Any) -> dict[str, Any]`; `load_scenario(path: Path, *, allowed_root: Path) -> dict[str, Any]`.

- [ ] **Step 1: Write failing tests** for Spec `8 synthetic fixture: `training_readiness_pct=68`, `patch_compliance_pct=74`, `sensor_health_pct=91`, seed=0; stable reordered-field hash; reject Boolean metrics, NaN/Infinity, non-synthetic Warfighter record even when PUBLIC, unknown fields, symlink escape, path traversal, invalid UTF-8, and >64 KiB inputs.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_fixtures -v`. Expected RED.
- [ ] **Step 3: Implement** strict top-level fixture contract, metric allowlist, percentages 0-100, bounded nonnegative alerts, explicit source rights, file lstat and canonical path confinement. No remote fetches, implicit DB creation or auto-upgrade to verified.
- [ ] **Step 4: Run** focused test. Expected GREEN and no file outside test workspace modified.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/fixtures.py research_lab/warfighter/examples research_lab/warfighter/tests/test_fixtures.py && git commit -m "feat(warfighter): add safe synthetic fixture boundary"`.

### Task 3: Reproducible Baseline Engine

**Files:** Create `research_lab/warfighter/baseline.py`, `research_lab/warfighter/tests/test_baseline.py`.

**Interface:** `run_baseline(scenario: dict[str, Any], *, what_if_delta: int = 5) -> dict[str, Any]`. Output `metrics[name]={"baseline": int, "hypothetical": int, "gap_to_100": int}` for allowed percentage metrics. `hypothetical=min(100, baseline+delta)`, `gap_to_100=100-baseline`. No combined readiness score or operational prediction.

- [ ] **Step 1: Write failing tests** checking 68→73, 74→79, 91→96, clamp 99→100, stable repeated results, no mutation, no readiness aggregate, and rejection of delta True/-1/21.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_baseline -v`. Expected RED.
- [ ] **Step 3: Implement** pure sorted arithmetic and output tags `synthetic=true`, `authority=RESEARCH_ONLY`, `interpretation="hypothetical exercise, not forecast"`.
- [ ] **Step 4: Run** focused test. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/baseline.py research_lab/warfighter/tests/test_baseline.py && git commit -m "feat(warfighter): deterministic synthetic what-if engine"`.

### Task 4: Exact Mathematics Reuse (No XQE Dispatch)

**Files:** Create `research_lab/warfighter/hilbert_adapter.py`, `research_lab/warfighter/tests/test_math_adapter.py`.

**Interfaces:** `analyze_math(engine: str, problem: dict[str, Any]) -> dict[str, Any]` and `verify_math(engine: str, report: dict[str, Any]) -> bool`; engines `bio-hilbert` and `exact-linear` only. Delegate to `research_lab.bio_hilbert.analyze/verify` and `research_lab.multidimensional.analyze/verify`, not the task-dispatching `workers.xqe`.

- [ ] **Step 1: Write failing tests** using `research_lab/examples/bio_hilbert_6_to_infinity.json`, expecting 36 finite coordinates, replayable report, rejecting 129 modes and 9 steps; test exact-linear nonnormal fixture verifies, and mathematically INCONCLUSIVE remains explicitly inconclusive.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_math_adapter -v`. Expected RED.
- [ ] **Step 3: Implement** bounded dispatcher, unchanged mathematical assumptions and truth labels, and pure function routing without network/process/task dispatch.
- [ ] **Step 4: Run** `python3 -m unittest research_lab.warfighter.tests.test_math_adapter research_lab.tests.test_bio_hilbert research_lab.tests.test_multidimensional -v`. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/hilbert_adapter.py research_lab/warfighter/tests/test_math_adapter.py && git commit -m "feat(warfighter): reuse certified exact research math"`.

### Task 5: Run Envelopes and Independent Replay

**Files:** Create `research_lab/warfighter/artifact.py`, `research_lab/warfighter/verify.py`, `research_lab/warfighter/tests/test_verify.py`.

**Interfaces:** `build_run(*, run_id: str, scenario: dict[str, Any], engine: str, output: dict[str, Any], code_sha256: str, generated_at: str) -> dict[str, Any]`; `verify_run(run: dict[str, Any]) -> dict[str, Any]` returning `{"status": "VERIFIED_FOR_MODEL"|"FAILED"|"INCONCLUSIVE", "run_sha256": str, "method": str}`. Re-run the stored declarative input, compare the canonical output and recompute an owned module's actual file digest; never trust an embedded status.

- [ ] **Step 1: Write failing tests** for reproducible input/result digests, 64-hex-lowercase code hash, timestamp parsing, rejecting >1 MiB output, tampered model/output/code/status, mathematical INCONCLUSIVE not becoming PROVED, and no fake certificate accepted.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_verify -v`. Expected RED.
- [ ] **Step 3: Implement** immutable-style envelope with truth labels, scope and replay metadata. The verifier uses pinned engine-id→local source mapping; any disagreement returns FAILED without side effects.
- [ ] **Step 4: Run** focused test and `python3 -m unittest research_lab.tests.test_bio_hilbert -q`. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/artifact.py research_lab/warfighter/verify.py research_lab/warfighter/tests/test_verify.py && git commit -m "feat(warfighter): bind model outputs to replayed evidence"`.

### Task 6: Local Quarantine and Explicit Review

**Files:** Create `research_lab/warfighter/journal.py`, `research_lab/warfighter/tests/test_journal.py`.

**Interfaces:** `ResearchJournal(workspace: Path)` (local SQLite with 0700 dir and 0600 file), with `record_run(run: dict) -> str`; `record_verification(run_id: str, result: dict) -> None`; `record_review(run_id: str, *, reviewer: str, decision: str, rationale: str, confirmed: bool) -> dict`; `get_run(run_id: str) -> dict`; `close() -> None`. Allowed review decisions `APPROVE` or `REJECT`. Review binds verified digest in one database transaction; reviewer is a **local user-supplied label**, not an authenticated military identity.

- [ ] **Step 1: Write failing tests**: unverified / modified artifact cannot approve; `confirmed=False` fails; merely editing artifact JSON approval field is ignored; duplicate ID conflicts unless byte-identical; symlink workspace escape rejected; concurrent approval attempts yield a single decision event.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_journal -v`. Expected RED.
- [ ] **Step 3: Implement** append-only application events, ordered sequence, digest-linked audit, transactional state changes; only explicit review call can record approval. Do not claim tamper-proof or independently authenticated reviewer.
- [ ] **Step 4: Run** focused test twice in same temporary workspace. Expected GREEN, no duplicate event.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/journal.py research_lab/warfighter/tests/test_journal.py && git commit -m "feat(warfighter): journal verified research and human review"`.

### Task 7: Research-Only Publication and Revocation

**Files:** Create `research_lab/warfighter/publication.py`, `research_lab/warfighter/tests/test_publication.py`.

**Interfaces:** `publish_reviewed(journal: ResearchJournal, run_id: str) -> dict[str, Any]`; `revoke_finding(journal: ResearchJournal, publication_id: str, *, reason: str) -> dict[str, Any]`; `list_findings(journal: ResearchJournal, *, approved_only: bool = True) -> list[dict[str, Any]]`. All projections remain `RESEARCH_ONLY`, with review/certificate/source links.

- [ ] **Step 1: Write failing tests**: cannot publish unverified, unreviewed, rejected, tampered, stale-digest, or revoked run; repeated identical publish creates exactly one event; revoke hides it from default results while keeping audit/tombstone; base ZYRA ontology SHA unchanged.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_publication -v`. Expected RED.
- [ ] **Step 3: Implement** fresh verification and decision-binding checks within publication transaction; build derived overlay from approved events, not model output or editable JSON field; support revocation/rebuild without operational authority edges.
- [ ] **Step 4: Run** focused test and `python3 -m pytest -q tests/test_zyra_mss.py` if pytest installed. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/publication.py research_lab/warfighter/tests/test_publication.py && git commit -m "feat(warfighter): publish approved results only to research overlay"`.

### Task 8: Opt-In PINEAL Research Projection

**Files:** Create `research_lab/warfighter/pineal_projection.py`, `research_lab/warfighter/tests/test_pineal_projection.py`; do **not** modify existing PINEAL `federation.py`.

**Interfaces:** `project_approved_finding(journal: ResearchJournal, publication_id: str, *, pineal_db: Path) -> dict[str, Any]`; `reconcile_pineal_projection(journal: ResearchJournal, publication_id: str, *, pineal_db: Path) -> dict[str, Any]`. Only when explicitly requested, call installed `pineal.store.PinealStore.put` with `namespace="warfighter_research"`, minimal digest/summary/provenance, and locally tracked returned record ID/version.

- [ ] **Step 1: Write failing tests**: simulate/verify/findings do not create PINEAL DB; approved explicit projection creates one namespace triple, audited; repeat is idempotent; revoked finding is marked revoked or flagged STALE; PINEAL outage records PARTIALLY_PROJECTED; nonsynthetic `warfighter-defense-si` writes still fail.
- [ ] **Step 2: Run** `PYTHONPATH=integrations/gpt-doug-pineal/src:. python3 -m unittest research_lab.warfighter.tests.test_pineal_projection -v`. Expected RED.
- [ ] **Step 3: Implement** opt-in adapter with no default path auto-creation, explicit reconciliation, research journal as current truth; never project real readiness, credentials or sensitive source text.
- [ ] **Step 4: Run** same test and `PYTHONPATH=integrations/gpt-doug-pineal/src:. python3 -m pytest -q integrations/gpt-doug-pineal/tests/test_federation_store.py integrations/gpt-doug-pineal/tests/test_store.py` if pytest installed. Expected GREEN.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/pineal_projection.py research_lab/warfighter/tests/test_pineal_projection.py && git commit -m "feat(warfighter): project approved studies into PINEAL research namespace"`.

### Task 9: Guarded CLI, Public Docs, End-to-End Acceptance

**Files:** Create `research_lab/warfighter/cli.py`, `research_lab/warfighter/tests/test_cli_e2e.py`, `docs/WARFIGHTER_RESEARCH_CLI.md`; modify `scripts/doug-max` and `docs/WARFIGHTER_RESEARCH_ONTOLOGY.md`.

**Interface:** `main(argv: list[str] | None = None) -> int` with subcommands `status`, `ontology --validate`, `scenario validate FILE`, `simulate FILE --engine baseline|bio-hilbert|exact-linear --workspace WORKSPACE`, `verify RUN_ID`, `review RUN_ID --decision approve|reject --reviewer LABEL --rationale TEXT`, `publish RUN_ID`, `findings`, `revoke PUBLICATION_ID --reason TEXT`, `pineal-project PUBLICATION_ID --pineal-db PATH`, `doctor`. For `scenario` and `simulate` require `--input-root ROOT`; enforce file confinement. All writes use explicit `--workspace WORKSPACE`, default private local research home only for read-only status. Approval requires explicit TTY confirmation of artifact digest.

Exit codes: 0 success, 2 invalid input, 3 failed verification, 4 unapproved, 5 limit, 6 optional dependency absent, 7 conflict.

- [ ] **Step 1: Write failing `test_cli_e2e.py`** for synthetic fixture simulate→verify→review (mock confirmed TTY)→publish→findings, rejection without review/non-TTY approval, no network/daemon/dispatch, truthful JSON statuses, revocation and 0 external calls. Mock XQE `run`/`verify` and `ontology.submit_task_action` to raise if called.
- [ ] **Step 2: Run** `python3 -m unittest research_lab.warfighter.tests.test_cli_e2e -v` and baseline `bash -n scripts/doug-max`. Expected RED on missing new command; if bash syntax is already broken on main, record and repair only that blocking parser issue in this task.
- [ ] **Step 3: Implement** command parser, guarded wrapper without new unconditional preflight exemption, user docs and exact sample output. Mark **only verified shipped pieces** implemented in public docs; planned quantum/geometry/Blender remains planned.
- [ ] **Step 4: Run full check:**
  - `python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v`
  - `python3 -m unittest research_lab.tests.test_bio_hilbert research_lab.tests.test_multidimensional -v`
  - `python3 -m pytest -q tests/test_zyra_mss.py`, if installed
  - `PYTHONPATH=integrations/gpt-doug-pineal/src:. python3 -m pytest -q integrations/gpt-doug-pineal/tests/test_federation_store.py`, if installed
  - `bash -n scripts/doug-max` and `bash scripts/doug-max warfighter doctor`
  - `git diff --exit-code main -- safety-shield/ontology/zyra-mss-v1.json integrations/gpt-doug-pineal/src/pineal/federation.py workers/xqe.py`
  Expected pass on supported environment and no base authority changes. Record actual outputs, not optimistic test counts.
- [ ] **Step 5: Commit** `git add research_lab/warfighter/cli.py research_lab/warfighter/tests/test_cli_e2e.py scripts/doug-max docs/WARFIGHTER_RESEARCH_CLI.md docs/WARFIGHTER_RESEARCH_ONTOLOGY.md && git commit -m "feat(warfighter): guarded research CLI and acceptance checks"`.

## Integration, Review, Release

Before requesting merge, run an independent whole-branch review emphasizing unsafe field promotion, artificial approvals, PINEAL projection staleness, external side effects and XQE isolation. Run full tests and document any known baseline failures; a JSON policy declaration alone is not an enforcement mechanism. Only implementation evidence may change the canonical public document's status to IMPLEMENTED.

This plan ships M0–M2. Independent mathematically creative engines and 6D/10D/11D visualization are covered in `docs/superpowers/plans/2026-10-12-quantum-lens-visualization.md`. Do not implement either plan until the human reviews the written plans and selects execution method.
