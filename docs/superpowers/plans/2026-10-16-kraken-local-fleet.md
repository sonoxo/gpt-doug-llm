# Kraken Local Fleet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an operator-controlled, foreground planner/reviewer runtime using explicitly approved local models after BioChip foundation hardening passes.

**Architecture:** A deterministic supervisor owns admission, budgets, identity and stop handling. It runs fixed, bounded inference worker processes, records metadata in a private ledger and returns unverified model proposals for human review. No model-generated tool, shell command, actor or approval is executable authority.

**Tech Stack:** Python 3.10+ standard library; the hardened BioChip router; SQLite; subprocess; selectors; POSIX process/file controls; unittest. No Node dependency or paid API is needed for this phase.

**Spec:** `docs/superpowers/specs/2026-10-16-kraken-local-fleet-design.md`, sections 5-7 and phase 2 of section 10. Required predecessor: `docs/superpowers/plans/2026-10-16-biochip-hardening.md`.

**Status:** Plan awaiting review; no runtime or launch command exists as a result of this document. Start implementation only from the reviewed, passing hardening commit, whose actual SHA must be recorded in the implementation PR.

## Global Constraints

- Defaults: one active model request, queue capacity 32, at most eight model calls and ten tool calls per mission, 1,024 generated tokens per model call, and a ten-minute mission deadline.
- Reject oversized prompts or tool replies above 1 MiB before passing them onward.
- No automatic weight downloads, cloud models, endpoint failover, arbitrary shell commands, imports chosen by a model, or execution of every module found in an agents directory.
- No automatic rearm and no interpretation of a model's text as an operator rearm command.
- Audit storage failure blocks action rather than silently losing evidence.
- No sudo, force reset, deletion of working repositories, shell-profile edits, automatic sign-in, background LaunchAgent, purchases or global package replacement.
- Phase 2 enables zero external tool calls; the ten-tool ceiling is reserved for a later reviewed broker, not permission to call tools now.
- The first release supports concurrency 1 only. Raising it to 2 requires the separately measured memory preflight allowed by the spec and is explicitly deferred; reject unsupported concurrency settings rather than silently scaling.

## Review Focus

1. A loopback model server proxies to a paid/cloud model: unknown or unapproved locality blocks execution; local API discovery alone is not proof (Task 1).
2. A child emits oversized output or stalls indefinitely: the supervisor enforces byte/deadline limits and terminates only its own worker (Task 3).
3. The process restarts after an inference intent was recorded: mark the result uncertain and never silently replay it (Task 2).
4. The same model is assigned both roles: report that fact instead of claiming independent model consensus (Task 4).
5. CLI environment cleanup removes a host stop override, or the active stop directory disappears: retain all stop controls and fail closed (Tasks 3 and 5).

## Scope and delivery dependency

This is a local inference fleet, not a swarm of independent ChatGPT sessions, a trained GPT-Doug foundation model, or a physical fleet. Native sequential implementation is the proposed method in the current environment; no independent subagent-dispatch capability has been demonstrated.

Phase 1 must be reviewed and its regression suite pass before Task 1 begins. Keep the user's existing checkout unchanged by using an isolated implementation branch/worktree. Do not automatically merge prior PRs. HeyPCB transport, remote approvals, fabrication, and the combined Node/Mac release are excluded and remain disabled until phases 3-4 have their own reviewed plans.

## File map

| New file | Responsibility |
| --- | --- |
| `biochip/fleet/__init__.py` | Export the public supervisor/configuration types only |
| `biochip/fleet/config.py` | Frozen limits, approved local model inventory and operator identity |
| `biochip/fleet/ledger.py` | Private metadata-only mission ledger and crash reconciliation |
| `biochip/fleet/worker.py` | Fixed one-request child inference entry point |
| `biochip/fleet/supervisor.py` | Queue, budgets, worker lifecycle and planner/reviewer flow |
| `biochip/fleet/__main__.py` | Operator CLI; no automatic daemon or remote tool execution |
| `biochip/tests/test_fleet_config.py` | Limits, identities, model admission |
| `biochip/tests/test_fleet_ledger.py` | Transitions, redaction, private storage, crash handling |
| `biochip/tests/test_fleet_worker.py` | Deadlines, output limits, own-process termination and stop controls |
| `biochip/tests/test_fleet_supervisor.py` | Queue, counters, role identity, proposal-only behavior |
| `biochip/tests/test_fleet_cli.py` | End-to-end local fixtures, command exits, no-launch diagnostics |
| `biochip/FLEET.md` | Operator use, exact scope and verification limits |

## Task 1: Limits and explicit model admission

**Files:** `biochip/fleet/config.py`, `biochip/fleet/__init__.py`, `biochip/tests/test_fleet_config.py`.

**Interfaces:** Define frozen `FleetLimits(max_inflight: int = 1, queue_capacity: int = 32, max_model_calls: int = 8, max_tool_calls: int = 10, max_output_tokens: int = 1024, deadline_seconds: float = 600.0, max_message_bytes: int = 1048576)`. Define frozen `ModelApproval(provider: str, name: str, endpoint: str, approved_by: str, approved_at: str, locality_evidence: str, license_evidence: str, operator_confirmed_local: bool)`. Define `FleetConfig(operator: str, project: str, planner: ModelApproval, reviewer: ModelApproval | None, limits: FleetLimits)` and `load_config(path: Path) -> FleetConfig`.

- [ ] Write tests asserting the exact defaults, positive finite limits, rejection of booleans as numbers, rejection of limits above those ceilings, and rejection of unknown fields. Test missing approvals, blank locality/license evidence, false locality confirmation, remote endpoint, absent installed model and a cloud-marked model. Admission requires both a reviewed inventory entry and matching current discovery, never just an advertised model name.

```python
limits = FleetLimits()
self.assertEqual((limits.max_inflight, limits.queue_capacity, limits.max_model_calls), (1, 32, 8))
self.assertEqual((limits.max_output_tokens, limits.deadline_seconds, limits.max_message_bytes),
                 (1024, 600.0, 1048576))
with self.assertRaises(ValueError):
    FleetLimits(max_inflight=2)
```

- [ ] Run `python3 -m unittest biochip.tests.test_fleet_config -v` and confirm the intended missing-interface failures.
- [ ] Implement strict config parsing using phase-1 validation and endpoint normalization. Validate evidence strings as references, not URLs to automatically fetch. Configuration is supplied by the operator and never overwritten or generated as approved by a model. State clearly that operator locality attestation does not provide technical proof about a separately configured server's backend.
- [ ] Run focused and full BioChip tests; prove the reviewed mapping cannot be mutated through a caller-owned dictionary.
- [ ] Commit only Task 1 files with `feat(kraken): add bounded local model admission contracts`.

## Task 2: Metadata ledger and interrupted-work reconciliation

**Files:** `biochip/fleet/ledger.py`, `biochip/tests/test_fleet_ledger.py`.

**Interfaces:** Define `MissionLedger(database: Path)` with `create(config: FleetConfig, prompt_sha256: str) -> str`, `transition(mission_id: str, *, expected: str, new: str, detail: dict[str, Any]) -> bool`, `record(mission_id: str, event: dict[str, Any]) -> None`, `read(mission_id: str, *, operator: str, project: str) -> dict[str, Any]`, and `reconcile_interrupted() -> int`. IDs are generated by the supervisor, never supplied by model text.

- [ ] Test legal transitions `queued -> running -> completed|failed|stopped|uncertain` and `queued -> stopped|uncertain`. Assert stale expected-state updates return false, cross-project reads fail, and fresh startup changes abandoned queued/running missions to uncertain without inference. Inject disk/commit errors and assert they propagate. Test that raw prompt, model text, tokens/keys/headers and arbitrary event fields cannot enter the ledger.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_ledger -v`; confirm failures before implementing the ledger.
- [ ] Use a private directory mode `0700`, database mode `0600`, schema version 1 and parameterized, explicit SQLite transactions. Permit only metadata fields: operator/project, model IDs, source/policy revisions, prompt/proposal/schema digests, state, times, counters and bounded reason codes. Unknown usage is null, not zero. A successful mutation of the ledger must commit before dispatch can begin. Reject future schema versions and symlink/nonregular targets. In-memory prompts are deliberately not recoverable; crash recovery never pretends otherwise.
- [ ] Run focused/full tests and verify a new ledger instance can read committed metadata. Do not reuse BioChip confidence values as an authorization or completion signal.
- [ ] Commit Task 2 files with `feat(kraken): record mission evidence and uncertain crash outcomes`.

## Task 3: Supervised one-request inference worker

**Files:** `biochip/fleet/worker.py`, `biochip/fleet/supervisor.py`, `biochip/tests/test_fleet_worker.py`.

**Interfaces:** Worker entry `main() -> int` consumes one bounded UTF-8 JSON request from stdin and emits one bounded JSON result to stdout. Internal request fields are exact approved provider/model/endpoint, prompt, system, max_tokens and timeout. Consume phase-1 `ModelRouter.chat_result(...) -> ChatResult`. Define supervisor helper `run_inference(approval: ModelApproval, prompt: str, *, system: str, limits: FleetLimits, deadline: float) -> ChatResult`; the absolute deadline uses `time.monotonic()`.

- [ ] Write fixture tests for a valid response, malformed child output, an oversized reply, a child that never replies, a flooding stderr stream and STOP before/during inference. Assert worker termination leaves an unrelated sentinel process alive. Verify the child receives `GPT_DOUG_AI_BLOCK_ALL`, `GPT_DOUG_AI_STOP_DIR` and `GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY` unchanged but no cloud/API-key environment variables. Assertions distinguish local cancellation from cancellation of server-side generation.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_worker -v`; demonstrate the missing bounded worker behavior.
- [ ] Spawn only `[sys.executable, '-I', absolute_verified_worker_path]` with `shell=False`, stdin/stdout/stderr pipes and a curated environment. The worker adds only its own canonical repository root to imports; no model-chosen command, module or path is accepted. Preserve the real HOME and the three stop-control variables. Use bounded, nonblocking pipe reads with selectors; no unbounded `communicate()` buffer. Poll STOP and the mission deadline at most every 0.2 seconds. On cancellation terminate only the child this supervisor created, then wait up to two seconds before killing that same child if necessary. Close pipes and reap the child on all paths.
- [ ] Run tests with actual local fixture processes. Confirm response-byte bounds are enforced even if the child lies about lengths. Document that a Python subprocess is not an OS sandbox and a stopped client may leave generation running in the separate local model server.
- [ ] Commit Task 3 files with `feat(kraken): supervise bounded inference child processes`.

## Task 4: Deterministic queue and proposal-only planner/reviewer

**Files:** `biochip/fleet/supervisor.py`, `biochip/tests/test_fleet_supervisor.py`.

**Interfaces:** Define `FleetSupervisor(config: FleetConfig, ledger: MissionLedger)` with `submit(prompt: str) -> str` and `run_pending() -> list[dict[str, Any]]`. Consume Task 3 `run_inference`. Fixed role instructions are maintained in this module; model text cannot supply the role, identity, configuration or executable behavior.

- [ ] Test a queue of 32 waiting requests and rejection of the 33rd, one in-flight inference, rejection before a ninth model call, a maximum of 1,024 requested output tokens and mission expiry before new dispatch. Every attempted dispatched call counts, including failures. Tool-call count remains exactly zero. Test identical planner/reviewer IDs, reviewer failure, oversized combined context, STOP between roles, and a prompt that demands shell execution, another identity or approval.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_supervisor -v`; confirm failures before implementation.
- [ ] Acquire a nonblocking POSIX lock on a private persistent lock file for the runtime; do not delete the locked inode. A second supervisor using that state directory must fail clearly. Complete Task 2 crash reconciliation before dispatch. Record intent before each call, apply the remaining deadline, and recheck STOP after its result. Run one planner call and, when configured, one reviewer call; no self-growing loops or automatic retries. Results are unverified text/proposals, not executed actions. Record `independent_models=false` for identical role models; absence/failure of a reviewer cannot become a reviewed success.
- [ ] Run queue/state/role tests and the full suite. Assert model-supplied shell commands and fields named actor, approved or execute cause zero file/tool/process actions beyond the fixed inference child. Quoted planner output goes to the reviewer's user context, never its system instruction. Discard late results as uncertain/stopped rather than saving approved knowledge.
- [ ] Commit Task 4 files with `feat(kraken): run a bounded proposal-only planning fleet`.

## Task 5: Foreground operator CLI with explicit stop

**Files:** `biochip/fleet/__main__.py`, `biochip/FLEET.md`, `biochip/tests/test_fleet_cli.py`.

**Interfaces:** Define `main(argv: list[str] | None = None) -> int` for `doctor`, `inventory`, `plan`, `run`, `status` and `stop`. `plan` validates admission and displays roles/limits without inference. `run --config PATH` reads a bounded prompt from stdin, submits one mission and runs it in the foreground. `status --config PATH --mission ID` reads scoped metadata. `stop` calls the existing `ai_killswitch.emergency_stop`; there is no automatic resume. Exit codes: 0 verified requested success, 2 validation/configuration failure, 3 stopped, 4 unavailable/uncertain/provider failure.

- [ ] Test CLI subprocesses against localhost fixture servers: doctor performs discovery only; plan makes no generation call; run makes only the two selected model calls; status does not mutate state. Test nonexistent/malformed config, unavailable provider, empty stdin and UTF-8 size overflow. Test that missing authentication for future HeyPCB capability is never reported as ready; no HeyPCB connection is attempted at all.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_cli -v`; confirm expected failures before implementation.
- [ ] Emit machine-readable JSON with separate `discovery`, `inference`, `review`, `external_tools_enabled=false` and `macos_verified` fields. Distinguish untested/null from failed/false. Set `macos_verified` only from recorded Mac evidence, not by assuming a user's operating system. All shell examples use an existing checked-out module after it has been built; no install-through-curl, profile modification, model download or startup daemon. Reject unsupported `approve`, `execute-tool` or rearm operations rather than accepting them as no-ops.
- [ ] Run focused/full tests and `python3 -m biochip.fleet --help` after implementation. Keep the three stop-control variables unchanged. Write the actual launch/stop examples in FLEET.md only once those commands exist and their exit codes have been tested.
- [ ] Commit Task 5 files with `feat(kraken): add foreground fleet CLI and operator stop`.

## Task 6: Integrated acceptance and Mac handoff

**Files:** Extend `biochip/tests/test_fleet_cli.py`, `biochip/FLEET.md`; add a bounded evidence report under `docs/reviews/` only after actual execution.

**Interfaces:** Reuse Tasks 1-5 unchanged. Evidence fields are source commit, Python/SQLite/OS versions, selected provider/model IDs, exact command, exit code, test counts, metadata hashes and explicit skipped-check reasons. Do not store raw prompts, private model replies or secrets in repository evidence.

- [ ] Add an end-to-end fixture covering successful planning, stopped planning and interrupted planning with reconciliation. Add a lifecycle test that a worker or failed mission leaves no unreaped owned child and no automatic retry. Add an environment test showing the Python-only phase never invokes Node, npm, brew or the HeyPCB package.
- [ ] Run those tests before any final adjustments and record a genuine failing requirement when a fix is needed; do not manufacture a failure when existing behavior already meets the requirement.
- [ ] Make only the fixes required by these acceptance cases; update operator documentation with actual runtime behavior and remaining limits.
- [ ] Execute `python3 -m unittest discover -s biochip/tests -t . -v` and `git diff --check`; inspect the full branch diff. Record actual results rather than a projected test count. Re-run the four K regressions against this final commit.
- [ ] Obtain a real selected local-model smoke test on the operator's Mac using the approved inventory and a nonsensitive prompt. Record it separately from mock fixture results. When the Mac or model is unavailable, leave this check pending and keep the runtime release a draft. No claim of a live summoned fleet is permitted on mock-only evidence.
- [ ] Commit acceptance tests/docs with `test(kraken): verify bounded fleet lifecycle and record release evidence` and request review before merging. Do not fabricate a reviewer or independently reviewed status.

## Coverage and deferred gates

Phase-1 memory and transport requirements are covered by the predecessor plan. This plan covers the default single-worker local fleet, metadata persistence, budget/deadline enforcement, stop behavior, duplicate-model disclosure, crash uncertainty and foreground operation. Optional concurrency 2, free HeyPCB tool execution, approvals bound to live tool schemas, safe exports, hardware design and the combined Node 24 Mac build are not part of this release. Those features must remain disabled; none may be marked complete through these tests.

Review both plans before execution. Proposed method: native sequential implementation, phase 1 first, then this plan after its predecessor's test/review gate. A future environment with real subagent support may substitute independently reviewed task execution without weakening the same acceptance criteria.
