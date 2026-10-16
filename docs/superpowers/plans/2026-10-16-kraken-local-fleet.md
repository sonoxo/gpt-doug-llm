# Kraken Local Fleet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an operator-controlled, foreground planner/reviewer runtime using explicitly approved local models after BioChip foundation hardening passes.

**Architecture:** A deterministic supervisor owns admission, budgets, identity and stop handling. It runs fixed, bounded inference worker processes, records metadata in a private ledger and returns unverified model proposals for human review. Model-generated tools, shell commands, actor names and approvals are never executable authority.

**Tech Stack:** Python 3.10+ standard library; hardened BioChip router; SQLite; subprocess; selectors; POSIX process/file controls; unittest. No Node dependency or paid API is needed for this phase.

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
- The first release supports concurrency 1 only. Raising it to 2 requires the separately measured memory preflight allowed by the spec and is deferred; reject unsupported concurrency settings rather than silently scaling.

## Review Focus

1. A loopback server proxies to paid/cloud inference: unknown or unapproved locality blocks execution; API discovery alone is not proof (Task 1).
2. A child stalls without reading stdin or floods output: bounded nonblocking writes and reads enforce deadlines and terminate only the owned worker (Task 3).
3. The process restarts after an inference intent: mark the result uncertain and never silently replay it (Task 2).
4. The same model handles both roles: report that fact instead of claiming independent model consensus (Task 4).
5. Environment cleanup loses a stop override, or a required stop directory disappears: preserve controls and fail closed (Tasks 3 and 5).

## Scope and delivery dependency

This is a local inference fleet, not independent ChatGPT sessions, a trained foundation model, or a physical fleet. Native sequential implementation is the proposed method in this environment; no independent subagent-dispatch capability has been demonstrated.

Phase 1 must be reviewed and pass its regression suite before Task 1 begins. Use an isolated implementation branch/worktree; preserve the user's checkout and do not automatically merge prior PRs. HeyPCB transport, remote approvals, fabrication, and the combined Node/Mac release remain disabled until phases 3-4 have separately reviewed plans.

## File map

| New file | Responsibility |
| --- | --- |
| `biochip/fleet/__init__.py` | Public supervisor/configuration exports |
| `biochip/fleet/config.py` | Frozen limits, approved inventory, operator and state directory |
| `biochip/fleet/ledger.py` | Metadata-only mission ledger and crash reconciliation |
| `biochip/fleet/worker.py` | Fixed one-request child entry point |
| `biochip/fleet/supervisor.py` | Queue, budgets, child lifecycle and planner/reviewer flow |
| `biochip/fleet/__main__.py` | Foreground operator CLI |
| `biochip/tests/test_fleet_config.py` | Limits and model admission |
| `biochip/tests/test_fleet_ledger.py` | Transitions, redaction, storage, crash handling |
| `biochip/tests/test_fleet_worker.py` | I/O bounds, deadlines, owned-process termination, STOP |
| `biochip/tests/test_fleet_supervisor.py` | Queue, counters, roles, no tool execution |
| `biochip/tests/test_fleet_cli.py` | Integrated fixtures and command exit codes |
| `biochip/FLEET.md` | Actual operator commands and verification limits |

## Task 1: Limits and explicit model admission

**Files:** `biochip/fleet/config.py`, `biochip/fleet/__init__.py`, `biochip/tests/test_fleet_config.py`.

**Interfaces:** Define frozen `FleetLimits(max_inflight: int = 1, queue_capacity: int = 32, max_model_calls: int = 8, max_tool_calls: int = 10, max_output_tokens: int = 1024, deadline_seconds: float = 600.0, max_message_bytes: int = 1048576)`. Define frozen `ModelApproval(provider: str, name: str, endpoint: str, approved_by: str, approved_at: str, locality_evidence: str, license_evidence: str, operator_confirmed_local: bool)`. Define frozen `FleetConfig(operator: str, project: str, state_directory: Path, planner: ModelApproval, reviewer: ModelApproval | None, limits: FleetLimits)` and `load_config(path: Path) -> FleetConfig`. `state_directory` is an explicit absolute operator-selected path, never a model-controlled value. Its directory contains `missions.sqlite3` and `supervisor.lock`.

- [ ] Write `test_default_limits`, `test_rejects_invalid_limits`, `test_rejects_unapproved_models` and `test_state_directory_is_explicit`. Pin these assertions:

```python
limits = FleetLimits()
self.assertEqual((limits.max_inflight, limits.queue_capacity, limits.max_model_calls), (1, 32, 8))
self.assertEqual((limits.max_output_tokens, limits.deadline_seconds, limits.max_message_bytes),
                 (1024, 600.0, 1048576))
with self.assertRaises(ValueError):
    FleetLimits(max_inflight=2)
```

Also reject booleans, nonfinite/nonpositive limits, values above the stated ceilings, unknown fields, missing approval/evidence, false locality confirmation and remote endpoints. Runtime admission additionally requires a matching currently discovered model; parsing configuration alone does not prove a model is installed.

- [ ] Run `python3 -m unittest biochip.tests.test_fleet_config -v`; confirm intended missing-interface failures.
- [ ] Implement strict parsing with phase-1 validation/endpoint normalization. Evidence strings are references, not URLs to fetch. Require nonblank operator/project and approval identity plus a timezone-aware timestamp. Preserve approved configuration immutably. State clearly that operator attestation is not technical proof about a separately configured server's backend; no name-based filter can establish that all loopback inference is free or local.
- [ ] Run focused/full BioChip tests; verify mutation of input dictionaries cannot change the admitted configuration.
- [ ] Commit Task 1 files with `feat(kraken): add bounded local model admission contracts`.

## Task 2: Metadata ledger and interrupted-work reconciliation

**Files:** `biochip/fleet/ledger.py`, `biochip/tests/test_fleet_ledger.py`.

**Interfaces:** Define `MissionLedger(database: Path)` with read-only `database: Path` and methods `create(config: FleetConfig, prompt_sha256: str) -> str`, `transition(mission_id: str, *, expected: str, new: str, detail: dict[str, Any]) -> bool`, `record(mission_id: str, event: dict[str, Any]) -> None`, `read(mission_id: str, *, operator: str, project: str) -> dict[str, Any]`, and `reconcile_interrupted() -> int`. The supervisor constructs it at `config.state_directory / 'missions.sqlite3'` and owns generated mission IDs.

- [ ] Write `test_state_transitions`, `test_cross_project_denial`, `test_reconcile_without_replay`, `test_rejects_sensitive_event_fields` and `test_disk_failure_blocks_dispatch`. Permit `queued -> running -> completed|failed|stopped|uncertain` and `queued -> stopped|uncertain`; reject all other transitions. Assert:

```python
self.assertFalse(ledger.transition(mid, expected='completed', new='running', detail={}))
self.assertEqual(ledger.reconcile_interrupted(), 1)  # one abandoned fixture mission
self.assertEqual(ledger.read(mid, operator='owner', project='p')['state'], 'uncertain')
self.assertEqual(inference_fixture.calls, 0)
```

- [ ] Run `python3 -m unittest biochip.tests.test_fleet_ledger -v`; confirm failures before implementing the ledger.
- [ ] Use a private directory `0700`, database `0600`, schema version 1 and explicit SQLite transactions. Permit only metadata fields: operator/project, model IDs, source/policy revisions, prompt/proposal/schema digests, state, times, counters and bounded reason codes. Unknown usage is null, not zero. Reject arbitrary fields and raw prompt/model text/credentials. Propagate disk/commit errors and never dispatch without a committed intent. Reject future schemas and symlink/nonregular targets. In-memory prompts are deliberately unrecoverable after a crash.
- [ ] Run focused/full tests; reopen a separate ledger instance and verify committed records persist. Do not use a BioChip confidence score as an approval or completion signal.
- [ ] Commit Task 2 files with `feat(kraken): record mission evidence and uncertain crash outcomes`.

## Task 3: Supervised one-request inference worker

**Files:** `biochip/fleet/worker.py`, `biochip/fleet/supervisor.py`, `biochip/tests/test_fleet_worker.py`.

**Interfaces:** Worker `main() -> int` reads one bounded UTF-8 JSON request and emits one bounded JSON result. Request fields are exactly approved provider/model/endpoint, prompt, system, max_tokens and timeout. Consume phase-1 `ModelRouter.chat_result(...) -> ChatResult`. Define `run_inference(approval: ModelApproval, prompt: str, *, system: str, limits: FleetLimits, deadline: float) -> ChatResult`; the deadline is absolute `time.monotonic()` time.

- [ ] Write `test_valid_worker_response`, `test_malformed_worker_output`, `test_child_byte_limit`, `test_stalled_stdin_deadline`, `test_stderr_flood_deadline`, `test_stop_only_terminates_owned_child` and `test_stop_environment_preserved`. Assert blocked/flooding fixtures stop within the deadline plus bounded termination grace, the unrelated sentinel process remains alive, and no cloud/API-key variables enter the child's environment. Use fixture processes and event synchronization, not a real model account.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_worker -v`; confirm missing bounded behavior before implementation.
- [ ] Spawn only `[sys.executable, '-I', absolute_verified_worker_path]`, with `shell=False`. The fixed worker path is resolved from this package, not configuration or model output. It adds only its own canonical repository root to imports. Preserve real HOME and the three existing stop-control variables; exclude provider credentials. Supervise bounded nonblocking stdin writes AND stdout/stderr reads with selectors. Poll STOP/deadline at most every 0.2 seconds; never use unbounded `communicate()` buffering. On stop/timeout, terminate only the owned child, wait up to two seconds, then kill that same child if necessary. Close pipes and reap it on every exit path.
- [ ] Run actual local process fixtures; verify false length fields cannot bypass caps. Document that this subprocess is not an OS sandbox and stopping the client does not prove generation stopped in a separate model server.
- [ ] Commit Task 3 files with `feat(kraken): supervise bounded inference child processes`.

## Task 4: Deterministic queue and proposal-only planner/reviewer

**Files:** `biochip/fleet/supervisor.py`, `biochip/tests/test_fleet_supervisor.py`.

**Interfaces:** Define `MissionBudget(limits: FleetLimits, deadline: float)` with `model_calls: int`, `tool_calls: int`, `claim_model_call(now: float) -> None` and `remaining_seconds(now: float) -> float`; both methods raise `ValueError` on deadline/budget exhaustion. Define `FleetSupervisor(config: FleetConfig, ledger: MissionLedger)` with `submit(prompt: str) -> str` and `run_pending() -> list[dict[str, Any]]`. Use a new budget for each mission and Task 3 for inference. Only fixed role instructions originate in this module.

- [ ] Write `test_waiting_queue_capacity`, `test_model_budget_ceiling`, `test_single_inflight`, `test_identical_role_models_disclosed`, `test_reviewer_failure_not_reviewed_success`, `test_prompt_cannot_authorize_tools`, and `test_stop_between_roles`. Assert 32 waiting submissions accepted, the 33rd refused, requested tokens never exceed 1024 and tool count stays zero. Exercise the budget directly:

```python
budget = MissionBudget(FleetLimits(), deadline=600.0)
for _ in range(8):
    budget.claim_model_call(now=0.0)
with self.assertRaises(ValueError):
    budget.claim_model_call(now=0.0)
self.assertEqual(budget.model_calls, 8)
self.assertEqual(budget.tool_calls, 0)
```

- [ ] Run `python3 -m unittest biochip.tests.test_fleet_supervisor -v`; confirm expected failures before implementation.
- [ ] Acquire a nonblocking POSIX lock at `config.state_directory / 'supervisor.lock'` for the running supervisor; never delete the locked inode. Refuse a second owner. Reconcile Task 2 interrupted records only after locking. Commit intent and reserve the call budget immediately before each dispatch; failed attempts consume budget. Run one planner call plus an optional reviewer call, with no automatic retries or self-growing loops. Treat results as unverified proposals. Report `independent_models=false` for identical role models; reviewer failure cannot become a reviewed success.
- [ ] Run queue/state/role/full tests. Assert model-supplied commands, actor/approved fields and adversarial memory cause zero external tool/file actions. Review context contains quoted planner data in the user message, never as system authority. Reject combined oversized context and late results. Recheck STOP before recording successful completion.
- [ ] Commit Task 4 files with `feat(kraken): run a bounded proposal-only planning fleet`.

## Task 5: Foreground operator CLI with explicit stop

**Files:** `biochip/fleet/__main__.py`, `biochip/FLEET.md`, `biochip/tests/test_fleet_cli.py`.

**Interfaces:** Define `main(argv: list[str] | None = None) -> int` for `doctor`, `inventory`, `plan`, `run`, `status` and `stop`. All commands except stop accept `--config PATH`. `plan` validates admission and displays roles/limits without inference; `run` reads a bounded prompt from stdin and runs one mission in the foreground; `status` additionally requires `--mission ID`. Doctor/inventory read only and do not create a ledger. Stop calls existing `ai_killswitch.emergency_stop`; no automatic resume. Exit codes are 0 verified requested success, 2 validation/configuration failure, 3 stopped, 4 unavailable/uncertain/provider failure.

- [ ] Write `test_doctor_discovery_only`, `test_plan_no_inference`, `test_run_selected_roles`, `test_status_read_only`, `test_invalid_config_exit`, `test_prompt_byte_limit_exit`, `test_disabled_tools_never_connect` and `test_stop_environment_cli`. Verify command exit codes, exact selected-model call count, empty-input rejection and preserved stop controls with localhost fixtures. No HeyPCB connection is attempted.
- [ ] Run `python3 -m unittest biochip.tests.test_fleet_cli -v`; confirm failures before implementation.
- [ ] Emit JSON separating discovery, inference, review and `external_tools_enabled=false`; represent untested checks as null, not success. Record observed OS separately from verified macOS acceptance evidence. Never infer that earlier Node repair succeeded. Add no installer, sign-in, model download or startup daemon. Reject unsupported approve/execute-tool/rearm commands rather than returning successful no-ops. Status opens an existing ledger read-only; other diagnostic commands do not mutate state.
- [ ] Run focused/full tests and `python3 -m biochip.fleet --help` after implementation. Publish actual launch/stop commands in FLEET.md only after they exist and their exits have been tested. Preserve host stop overrides and the required stop-directory setting.
- [ ] Commit Task 5 files with `feat(kraken): add foreground fleet CLI and operator stop`.

## Task 6: Integrated acceptance and Mac handoff

**Files:** Extend `biochip/tests/test_fleet_cli.py`, `biochip/FLEET.md`; add bounded evidence under `docs/reviews/` only after execution.

**Interfaces:** Reuse Tasks 1-5. Evidence records source commit, Python/SQLite/OS, model IDs, exact commands/exits/counts, metadata hashes and skipped-check reasons, never raw prompts or private replies.

- [ ] Write `test_end_to_end_planning_lifecycle`, `test_interrupted_mission_not_replayed`, `test_no_owned_children_leaked` and `test_python_phase_does_not_require_node`. Cover success, stop and reconciliation; assert no Node/npm/brew/HeyPCB invocation.
- [ ] Run those tests before any final adjustments; record a real failing requirement only when a fix is needed, not a manufactured red result.
- [ ] Apply only fixes required by these acceptance cases and document actual behavior/limits.
- [ ] Execute `python3 -m unittest discover -s biochip/tests -t . -v` and `git diff --check`; inspect the complete diff and re-run K-01 through K-04 at the final commit. Record actual results, not projected counts.
- [ ] Obtain a separately recorded real local-model smoke test on the operator's Mac with approved inventory and a nonsensitive prompt. When Mac/model access is unavailable, leave verification pending and the runtime release draft. Mock-only results never prove a live fleet was summoned.
- [ ] Commit acceptance evidence with `test(kraken): verify bounded fleet lifecycle and record release evidence`; request review before merging. Do not fabricate independent reviewers.

## Coverage and deferred gates

Phase-1 memory/transport requirements are in the predecessor plan. This plan implements default single-worker planning, metadata persistence, budgets/deadlines, stop behavior, duplicate-model disclosure, crash uncertainty and foreground operation. Optional concurrency 2, HeyPCB operations, live-schema action approvals, safe exports, hardware design and the combined Node 24 Mac build remain disabled and are not claimed complete.

Review both plans before execution. Proposed method: native sequential implementation, hardening first, then this plan after its predecessor's test/review gate. An environment with genuine subagent support may substitute independently reviewed task execution without weakening the acceptance criteria.
