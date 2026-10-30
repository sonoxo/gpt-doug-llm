# BioChip Foundation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the four recorded memory/router failures and establish a testable foundation for the local Kraken fleet.

**Architecture:** Preserve the BioChip public API while making ownership checks transactional, denial auditing durable, numeric validation finite, and HTTP routing fail closed. Keep inference separate from memory authority and use the existing cooperative stop gate. No external tools or background workers are enabled by this phase.

**Tech Stack:** Python 3.10+ standard library; SQLite; urllib; unittest; local HTTP fixtures. Python 3.10 compatibility is an implementation requirement carried forward from the Mac build; newer Python-only APIs must not be required.

**Spec:** `docs/superpowers/specs/2026-10-16-kraken-local-fleet-design.md`, sections 3, 5-7 and phase 1 of section 10. Design revision: `dfa794ed7375d12b4f5997e0b774acba9185960b`.

**Status:** Plan awaiting review; no implementation tasks completed. The prior baseline report is evidence from the earlier review, not a new test run for this plan.

## Global Constraints

- Keep `remember`, `recall`, `forget`, `heartbeat` and `audit_trail` compatible.
- No automatic weight downloads, cloud models, endpoint failover, arbitrary shell commands, imports chosen by a model, or execution of every module found in an agents directory.
- Reject oversized prompts or tool replies above 1 MiB before passing them onward.
- Audit storage failure blocks action rather than silently losing evidence.
- No automatic rearm and no interpretation of a model's text as an operator rearm command.
- No sudo, force reset, deletion of working repositories, shell-profile edits, automatic sign-in, background LaunchAgent, purchases or global package replacement.
- These controls protect a trusted single-user runtime; caller-supplied actor names are not authentication and hashes are not tamper-proof signatures.

## Review Focus

1. Two BioChip instances race to create or replace the same key: exactly one owner wins and no second owner can change the value (Task 2).
2. Audit insertion or commit fails: no successful mutation is returned and the memory write rolls back (Task 2).
3. Multibyte text or deeply nested JSON bypasses a character-based limit: reject excessive encoded bytes and report malformed JSON as a validation/protocol error (Tasks 1 and 5).
4. STOP changes during inference or invalid stop configuration is present: do not return or save the result as successful (Task 6).
5. Endpoint configuration is changed after construction: no connection can escape the original reviewed endpoint mapping (Task 4).

## Source and execution boundary

The inspected code is PR #436 at `a09ae92e61c5ea389e5fa774bbffebde669f90e7`; it contains the earlier BioChip core. PR #437 is documentation-only on main and does not itself contain the BioChip package. Start the eventual implementation in an isolated branch/worktree based on the verified PR #436 head, not by switching or resetting the user's working checkout. Refresh PR heads before execution and stop to reconcile any change. Carry this plan and its spec into the implementation branch without assuming either dependency PR has merged.

Recommended execution in the current chat environment is native, sequential implementation. There is no independent subagent-dispatch tool exposed here; do not describe sequential work or test processes as an independently reviewing AI fleet. Each task may be handed to a separate implementer in an environment that actually supports that capability.

## File map and interfaces

| File | Responsibility |
| --- | --- |
| Modify `biochip/core.py` | Existing public memory methods; transactions, audit outcomes, schema version and backup |
| Create `biochip/validation.py` | Finite numbers, integer limits, UTF-8 field limits and bounded JSON |
| Create `biochip/transport.py` | Immutable loopback endpoint configuration and no-redirect HTTP transport |
| Modify `biochip/models.py` | Provider protocol validation, compatibility wrappers, inference results, stop checks |
| Create `biochip/tests/test_memory_security.py` | K-01/K-02, concurrency, storage and failure-atomicity regressions |
| Create `biochip/tests/test_model_security.py` | K-03/K-04, transport bounds, response validation, stop and trust-boundary regressions |
| Modify `biochip/tests/test_models.py` | Correct the old test that expects retrieved memory in a system message |
| Modify `biochip/README.md`, `biochip/OPEN_MODELS.md` | Exact changed contracts and remaining limitations |

Existing signatures remain callable. Add `BioChip.backup(destination: str) -> None`. Add frozen `ChatResult(text: str, provider: str, model: str, elapsed_seconds: float, reported_output_tokens: int | None)` and `ModelRouter.chat_result(model: Model, prompt: str, *, system: str = '', max_tokens: int = 512) -> ChatResult`; retain `chat(...) -> str` as a wrapper returning `.text`. `chat_with_memory(...)` continues returning a string and never saves by default.

## Task 1: Finite, bounded input validation (K-02)

**Files:** Create `biochip/validation.py`; modify `biochip/core.py`; test `biochip/tests/test_memory_security.py`.

**Interfaces:** Produce `finite_number(value: Any, *, name: str, minimum: float, maximum: float | None = None, exclusive_minimum: bool = False) -> float`, `bounded_text(value: Any, *, name: str, max_bytes: int) -> str`, and `encode_json(value: Any, *, max_bytes: int = 1048576) -> bytes`. Reject booleans as numbers, non-string identifiers, empty identifiers, NaN, infinities and serialization failures. Do not trim or otherwise silently change valid keys. New explicit bounds are 256 UTF-8 bytes for actor/key, 4,096 for provenance and 1,048,576 for the serialized value.

- [ ] Write `test_rejects_nonfinite_ttl_and_expiry_overflow`, `test_rejects_bool_confidence_and_ttl`, `test_utf8_value_byte_limit`, and `test_validation_does_not_write_memory` using a temporary file-backed BioChip. For each rejected input assert `ValueError` and zero newly stored rows. Pin representative assertions:

```python
for ttl in (float('nan'), float('inf'), -float('inf'), True, 0, -1):
    with self.assertRaises(ValueError):
        chip.remember('x', 1, actor='owner', provenance='test', ttl_seconds=ttl)
with self.assertRaises(ValueError):
    chip.remember('x', '\u00e9' * 1048576, actor='owner', provenance='test')
```

- [ ] Run `python3 -m unittest biochip.tests.test_memory_security -v`; confirm failures are the specified accepted inputs, not missing dependencies.
- [ ] Implement the helpers and validate finite `now + ttl_seconds` before opening a write transaction. Confidence must be finite and within `[0, 1]`; positive finite TTL or `None` remains the contract. Translate JSON recursion/encoding failures into `ValueError`. Reject out-of-bounds limits without coercing floats or strings to integers.
- [ ] Run the focused tests and `python3 -m unittest discover -s biochip/tests -t . -v`; update README with the explicit bounds and confirm ordinary existing values still round-trip.
- [ ] Commit only Task 1 files: `git add biochip/validation.py biochip/core.py biochip/tests/test_memory_security.py biochip/README.md && git commit -m 'fix(biochip): reject nonfinite and oversized memory inputs'`.

## Task 2: Failure-atomic ownership and durable denials (K-01)

**Files:** Modify `biochip/core.py`; test `biochip/tests/test_memory_security.py`.

**Interfaces:** Existing public methods retain their return types and `PermissionError` for cross-owner access. Internal transaction entry must acquire `BEGIN IMMEDIATE` before reading a memory owner whenever the operation may write memory or audit. Explicit transaction control uses a connection configured with `isolation_level=None`; initialization/migration has its own transaction and must not nest BEGIN inside executescript.

- [ ] Write tests for denied recall/replace/delete and integrity failure. Assert denial events are present, the original value is unchanged, and no event contains the value. Add a deterministic two-connection race, coordinated before transaction entry, asserting exactly one successful creator and one denial. Add an audit-failure fixture and a commit-failure fixture asserting no successful mutation and unchanged database contents.

```python
self.assertEqual([e['outcome'] for e in chip.audit_trail(actor='other')],
                 ['denied', 'denied', 'denied'])
self.assertEqual(chip.recall('x', actor='owner')['value'], 'original')
```

- [ ] Run `python3 -m unittest biochip.tests.test_memory_security -v`; record K-01 and race/failure results before the fix. Use events/barriers, not sleeps, for concurrency coordination.
- [ ] For known denials or integrity errors, insert the audit outcome without a memory mutation, exit and commit that transaction, then raise the domain exception. Unexpected exceptions always roll back. Never change the context manager to commit arbitrary exceptions. Retain owner-conditioned SQL mutations as defense in depth. Use the existing ten-second busy timeout; lock exhaustion is an explicit error, never an ownership bypass.
- [ ] Run focused and full BioChip tests; verify retry after a failed transaction still works. Document that audit failure itself is surfaced and cannot guarantee a durable denial record on an unavailable disk.
- [ ] Commit Task 2 files with `git commit -m 'fix(biochip): preserve denial audit and serialize ownership checks'` after explicitly staging only the listed files.

## Task 3: Private storage, compatible schema adoption and consistent backup

**Files:** Modify `biochip/core.py`, `biochip/README.md`; test `biochip/tests/test_memory_security.py`.

**Interfaces:** Produce `BioChip.backup(destination: str) -> None` using SQLite's backup API. Introduce `PRAGMA user_version=1` without changing existing memory/audit columns. Recognize the current schema as legacy version 0; reject incompatible or future schemas before changing them. Reject `:memory:` with an explanatory `ValueError`, since the current per-operation connection design cannot preserve it; file-backed persistence remains the supported contract.

- [ ] Test that a new database is owner-readable/writable only on POSIX, existing symlink/nonregular targets are refused, backup never overwrites, a legacy snapshot remains readable, and an unknown future version is untouched. Test that a failed backup prevents legacy schema adoption.
- [ ] Run `python3 -m unittest biochip.tests.test_memory_security -v`; record the expected pre-fix failures.
- [ ] Reserve new database/backup files with exclusive creation, no-follow where supported and mode `0600`; do not chmod an existing checkout or a whole home directory. Refuse existing group/world-accessible database files with remediation instructions. For a recognized legacy database, create a unique private consistent backup before setting version 1. Validate rows for nonfinite/invalid numeric state and fail with affected keys rather than silently deleting or rewriting records. State explicitly that same-UID malicious processes are outside the filesystem trust boundary.
- [ ] Run storage tests and the full suite; prove reopening preserves provenance/expiry/audit. Ensure temporary backup reservation is removed on failure without touching the source.
- [ ] Commit Task 3 files with `fix(biochip): secure storage and version legacy database adoption`.

## Task 4: Enforce loopback and byte limits at the HTTP boundary (K-04)

**Files:** Create `biochip/transport.py`; modify `biochip/models.py`; test `biochip/tests/test_model_security.py`.

**Interfaces:** Produce `normalize_loopback_url(url: str) -> str` and `request_json(base_url: str, path: str, payload: dict[str, Any] | None, *, timeout: float, max_bytes: int = 1048576) -> dict[str, Any]`. Accept only HTTP, the existing loopback names, a valid port and an empty/root base path. Canonicalize `localhost` to literal `127.0.0.1`; preserve literal IPv6 loopback. Reject credentials, control characters, query/fragment and non-loopback addresses. Expose a copied read-only `ModelRouter.endpoints` mapping with no setter; retain the `endpoints=None` default behavior and honor an explicitly empty mapping.

- [ ] Use local HTTP fixture servers to test GET and POST redirects for 301/302/303/307/308; assert the target receives zero requests. Test proxy environment variables, mutation of the caller's original dictionary, attempted mutation/reassignment of the exposed mapping, invalid ports and URL controls. Test 1 MiB+1 response bytes even with absent or false Content-Length, plus oversized request JSON.
- [ ] Run `python3 -m unittest biochip.tests.test_model_security -v`; record K-04 reproducing before the change. Fixtures must never contact an internet host.
- [ ] Build urllib's opener with `ProxyHandler({})` and a redirect handler that raises `HTTPError` for every redirect. Validate/canonicalize again just before opening. Read no more than `max_bytes + 1`, reject oversized responses before decoding, and close all responses on every path. Validate finite positive timeout before opening. Do not characterize socket inactivity timeout as an absolute deadline; phase 2 supplies a supervising deadline.
- [ ] Run the transport and existing model tests. Verify no API credential is included in errors or diagnostics and no fallback endpoint is contacted.
- [ ] Commit Task 4 files with `fix(biochip): reject redirects and freeze local endpoint configuration`.

## Task 5: Isolate malformed providers and keep reference data untrusted (K-03)

**Files:** Modify `biochip/models.py`, `biochip/tests/test_models.py`, `biochip/OPEN_MODELS.md`; test `biochip/tests/test_model_security.py`.

**Interfaces:** Preserve `discover() -> tuple[list[Model], dict[str, str]]`. Add `ProviderProtocolError(ValueError)` and the `ChatResult`/`chat_result` interface above. Report sanitized, provider-scoped errors; a malformed provider contributes no models while later valid providers still run. Missing usage is `None`, not invented zero. Preserve `chat` and `chat_with_memory` return types.

- [ ] Test non-list discovery fields, non-object entries, non-string IDs, duplicate IDs, invalid JSON, nested JSON exceeding decoder limits, missing/empty/null chat content and malformed usage. Assert healthy providers remain visible and no protocol failure becomes a successful empty answer. Test memory containing instruction-like text and prove it appears only as explicitly quoted reference data in a user message, not a system message.
- [ ] Run `python3 -m unittest biochip.tests.test_model_security -v`; record K-03 before fixing. Update only the unsafe expectation in the existing `test_explicit_memory`: check quoted user-prompt reference data and retain the no-default-save assertion.
- [ ] Validate provider containers and required fields; deduplicate `(provider, model)` pairs. Catch known provider/network/JSON failures per provider, not arbitrary programmer or stop-control errors. Validate reported token usage as nonnegative non-boolean integers when present. Implement `chat_result` and have `chat` return its text. Build memory context into the user prompt with explicit data delimiters; apply the aggregate encoded size limit after composition. Prompt formatting is not a complete prompt-injection defense; no tool-execution authority is granted here.
- [ ] Run focused and complete BioChip suites; verify both Ollama and compatible response shapes and unchanged string-based callers.
- [ ] Commit Task 5 files with `fix(biochip): validate provider responses and separate memory from instructions`.

## Task 6: Cooperative stop integration and the phase-1 verification gate

**Files:** Modify `biochip/models.py`, `biochip/OPEN_MODELS.md`; test `biochip/tests/test_model_security.py`. Reuse, do not rewrite, `ai_killswitch.py`.

**Interfaces:** Consume `ai_killswitch.require_ai_allowed(operation: str = 'AI execution') -> None` and `AIKillSwitchEngaged`. Perform checks before and after inference and before saving a reply; keep read-only discovery available for diagnostics while stopped. Import failures or invalid stop configuration fail inference closed. Do not catch a stop exception as an ordinary provider outage.

- [ ] Test a pre-existing stop latch, `GPT_DOUG_AI_BLOCK_ALL=1`, invalid stop configuration, STOP set by the HTTP fixture during generation and STOP before persistence. Assert no prohibited request or saved reply. Tests use private temporary stop directories and do not alter the real operator latch.
- [ ] Run `python3 -m unittest biochip.tests.test_model_security -v`; demonstrate the missing stop protection against the unchanged behavior.
- [ ] Wire checks through both `chat` and `chat_result` without double-counting requests, and through `chat_with_memory` before any save. Preserve host stop environment variables. Do not add a rearm path, background service or unrelated process termination.
- [ ] Execute `python3 -m unittest discover -s biochip/tests -t . -v` and `git diff --check`. Inspect the complete diff and verify all four K findings are covered. Record the actual commit, Python/SQLite/OS versions, commands, test counts and failures in the implementation PR. Prior 11-test results are not proof of the modified suite.
- [ ] Run the same focused suite on an actual Mac when available; otherwise explicitly leave macOS verification pending. Do not require Node for these Python-only tests, and do not assert the earlier Node repair succeeded.
- [ ] Commit Task 6 files with `fix(biochip): honor operator stop across inference and persistence`.

## Handoff and exclusions

After Tasks 1-6 pass and the change is reviewed, record that exact hardening commit as the input to `2026-10-16-kraken-local-fleet.md`. Do not merge PR #435/#436 automatically or claim every repository test is green. HeyPCB execution, credentials, approvals for external tools, manufacturing and the combined Node/Mac release remain phases 3-4 and require their own implementation plans. The phase-2 runtime must keep those capabilities disabled.

Review checkpoints: actual red/green evidence for each fix; no unplanned API break; no catch-all that converts security errors into success; no production secrets or remote internet endpoints in fixtures; no claims of independent reviewers unless those reviewers ran.

## Primary references

- Source: `biochip/core.py` and `biochip/models.py` at `a09ae92e61c5ea389e5fa774bbffebde669f90e7`; stop module at the same revision.
- Recorded earlier diagnostics: `docs/reviews/2026-10-16-kraken-baseline.json` (not rerun during planning).
- SQLite transaction semantics: https://www.sqlite.org/lang_transaction.html
- Python redirect handlers: https://docs.python.org/3.13/library/urllib.request.html#httpredirecthandler-objects
- SQLite backup API: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
