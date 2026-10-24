# GPT-Doug Kraken: local engineering fleet and HeyPCB integration

Date: 2026-10-16
Status: DRAFT DESIGN FOR REVIEW. No fleet runtime or HeyPCB integration is implemented by this document.
Scope: the BioChip / local-model / HeyPCB work discussed in this conversation, not every Sonoxo repository or existing Kraken simulation.

## 1. Intent and success criteria

Deliver GPT-Doug-LLM / GPT-Doug-MLM as an operator-controlled engineering workflow on the user's Mac: selected local models propose and review PCB-design actions; a deterministic broker validates permissions, cost policy and actual tool schemas; BioChip preserves approved knowledge and execution evidence. Provide a repeatable Mac build and an explicit stop control.

The user's established constraints are local-first inference, free-only operations, persistent ontology-oriented memory, real verification instead of simulated readiness, and terminal-delivered builds that preserve existing work. "Fleet" means bounded software workers on this authorized host. It does not mean physical robots, network propagation, new trained model weights, or an independently running service in ChatGPT.

Success is a tested local planning loop plus separately verified, authenticated, permitted HeyPCB calls. An unavailable or unknown-cost service must produce a blocked result, not fabricated success or fallback spending.

## 2. Inspected baseline and evidence

- GPT-Doug main: `82cfbf6f741b26b8a614e236ea1182a18d7285d6`.
- BioChip/model-router source: `a09ae92e61c5ea389e5fa774bbffebde669f90e7`, PR #436, depending on the BioChip branch from PR #435. PR #436 was still an open draft when inspected.
- HeyPCB fork: `ca2d97c41515c2a7c045d75f7882cfb3bac1eb43`.
- Five BioChip source/test files were retrieved through the GitHub connector and copied into an isolated Linux review directory. Every copied file matched its returned Git blob ID. This was not a full repository checkout: direct GitHub DNS resolution failed in the container.
- Fresh execution: 11 existing unit tests passed. Four additional diagnostic boundary checks failed. These results do not establish macOS compatibility, live inference, HeyPCB connectivity, or repository-wide CI success.

Companion evidence: `docs/reviews/2026-10-16-kraken-baseline.json`.

## 3. Release-blocking findings

| ID | Reproduced behavior | Required correction |
| --- | --- | --- |
| K-01 | Three denied memory operations raised PermissionError but left zero denial audit records. The surrounding transaction rolled back the audit insertion. | Persist a bounded denial event without committing any denied data change; test denial, integrity-error and success paths separately. |
| K-02 | A non-finite TTL was accepted and became a NULL expiry, leaving non-expiring memory. | Reject non-finite values and booleans for numeric limits; validate computed expiry before storage. |
| K-03 | A malformed model-list entry raised AttributeError and aborted discovery before the healthy provider was queried. | Validate each provider response and isolate protocol failures; retain healthy-provider results and diagnostics. |
| K-04 | An allowed initial HTTP endpoint redirected to a hostname the constructor rejects, and the router followed it. | Disable redirects, freeze/copy endpoint configuration, and validate the endpoint at the request boundary. |

The redirect reproduction contacted only local loopback test servers. It proves an allowlist bypass, not observed internet exfiltration. These four checks are diagnostic evidence against unchanged code, not fixes or a complete security audit.

## 4. Architecture decision

Choose a guarded local broker, rather than direct model-to-MCP access or a new cloud coordinator. Direct registration is smaller but omits shared policy and evidence handling. A cloud coordinator adds accounts, network exposure and costs without helping the initial single-Mac requirement.

Flow: operator request -> local planner -> optional local reviewer -> typed proposal -> policy/approval broker -> authenticated HeyPCB adapter -> checked result -> approved BioChip record.

Reuse the existing BioChip public methods, model-provider interfaces, MCP transport pattern in `xunia_godis.py`, and `ai_killswitch.require_ai_allowed`. Existing raw MCP commands must not become the fleet's bypass around the broker. No existing simulation is relabeled as a live fleet.

Proposed component boundaries are a fleet scheduler, proposal/policy module, HeyPCB transport adapter, evidence writer, and Mac build entry point. Final file layout and change-by-change implementation steps belong in the implementation plan after design review.

## 5. Local model fleet contract

Planner and reviewer are roles, not claims of independent intelligence. They may use different explicitly selected installed models; when the same model is used twice, report that fact. A deterministic verifier checks schemas, budgets and tool results. A deterministic recorder writes approved evidence.

Defaults: one active model request, queue capacity 32, at most eight model calls and ten tool calls per mission, 1,024 generated tokens per model call, and a ten-minute mission deadline. Concurrency may be raised to two by the operator after a measured memory preflight; no automatic scaling. Reject oversized prompts or tool replies above 1 MiB before passing them onward. Count model calls, tokens reported by providers, elapsed time, failures and skipped checks separately.

No automatic weight downloads, cloud models, endpoint failover, arbitrary shell commands, imports chosen by a model, or execution of every module found in an agents directory. An explicit reviewed model inventory records provider, model ID, locality, available license evidence and approval. A loopback API alone does not prove that its backend is local or free.

Discovery, a successful inference smoke test, and completed work are different states. Missing capabilities stay unknown or blocked. Provider protocol errors fail only the affected worker; authorization, stop-control, audit-storage and policy errors fail the mission closed.

## 6. Memory and evidence contract

Keep `remember`, `recall`, `forget`, `heartbeat` and `audit_trail` compatible. Correct the four baseline defects before routing tool work. Use transactional ownership checks that remain correct across multiple BioChip instances; an instance-local Python lock is not a cross-process permission guarantee.

The broker supplies the operator identity, project namespace and worker role. Model output must never select its own actor, widen visibility or mark itself approved. The initial deployment is single-user and trusted-local, not authenticated multi-tenant hosting. Any later network service requires a separate authenticated identity boundary.

Record mission ID, source revision, selected model IDs, schema digest, proposal digest, approval identity/time, tool outcome and artifact hashes. Store model statements as unverified proposals until reviewed. Retrieved memory is quoted data, not a higher-priority instruction. Do not persist credentials, authorization headers or raw prompts by default. Explicitly saved prompts remain subject to project permissions and retention settings.

Use finite numeric validation, bounded records, private state directories and schema-versioned migrations with a consistent backup. Audit storage failure blocks action rather than silently losing evidence. Hashes detect accidental changes; they are not signatures or protection against a malicious process that can rewrite the database.

## 7. Stop, approval and retry behavior

Check the repository's cooperative AI stop gate before scheduling, before and after inference, and immediately before every external tool call. Preserve the configured stop directory and host block setting through build/runtime environment sanitization. No automatic rearm and no interpretation of a model's text as an operator rearm command.

On stop, cease dispatch, cancel this runtime's pending work and mark uncertain in-flight results explicitly. Do not kill unrelated Ollama or user processes. An already accepted remote job may continue; local cancellation is not proof of remote rollback.

Each state-changing proposal is bound to a project, tool name, canonical arguments, live schema digest and policy revision. Approval expires after ten minutes and is consumed once. Argument, schema or policy changes invalidate approval. Record an intent before dispatch; after a crash, reconcile ambiguous outcomes instead of replaying mutations. Automatic retries are limited to one additional attempt for independently verified safe reads, within the original budget.

## 8. HeyPCB connection and free-only policy

Build and launch the pinned `sonoxo/heypcb-mcp` fork using an absolute Node executable and an argument vector, not a shell string or an unpinned `npx` download. The local package is a connector to HeyPCB's hosted service, not an offline copy of the PCB design engine.

Authentication is performed by the operator through HeyPCB's supported sign-in flow. Keep credentials confined to the connector process; do not send them to models or store them in BioChip. Do not assume that authentication completed because tool names are visible.

Read actual negotiated tool schemas. Reject generic offline placeholders, duplicate tool names, invalid schemas and unsupported protocol versions. A schema change invalidates the relevant approvals. Model-generated arguments are validated against the live schema and a separate reviewed tool/project allowlist. Do not invent request parameters for tools whose schemas are unavailable.

Free-only is a blocking policy, not a maximum budget promise: unknown cost, paid operations, credit purchases and manufacturing orders are prohibited. The README documents free rate-limited parts/circuit tools, but it does not establish a universal no-charge guarantee. A zero estimate, a balance of zero, or a read-only annotation is not sufficient authorization. Only reviewed documented-free operations with an enforceable no-charge contract may execute; if that cannot be established, emit a plan without calling the operation. Rate-limit failures never trigger a paid fallback.

MCP descriptions and annotations are hints, not enforcement. Tool results and suggested fixes are untrusted input; validate a suggested follow-up as a new proposal. Project creation, uploads, edits and exports all require an explicit scope and approval where permitted. Exports must stay within a chosen workspace, reject symlink/path escapes, use atomic writes, and never overwrite by default. Do not fetch model-supplied arbitrary download URLs.

## 9. Mac build and delivery contract

Produce a versioned, inspectable build entry point only after implementation is verified. It must use a fresh private staging directory, pinned source revisions and dependency locks, a private Python environment, and an explicitly selected Node 24 executable. Detect the actual Homebrew prefix instead of assuming Apple Silicon paths.

Test the selected Node executable and library linkage before dependency work; preserve diagnostics if the preflight fails. The user's last screenshot showed a broken Node 26 loader. This design does not assume the subsequent Node 24 repair succeeded.

No sudo, force reset, deletion of working repositories, shell-profile edits, automatic sign-in, background LaunchAgent, purchases or global package replacement. Do not skip security checks when a service is unreachable. Dependency installation disables lifecycle scripts; any required native build step must be individually reviewed and verified, not silently re-enabled.

Release manifests contain source revisions, dependency-lock hashes, toolchain versions, artifact hashes, exact checks and their results. Newly generated hashes provide later integrity checks, not independent publisher authentication. Keep the previous successful build until the new build passes its gates. Never advertise a terminal command for a path or release that has not been created and checked.

## 10. Delivery phases and acceptance

| Phase | Deliverable | Exit requirement |
| --- | --- | --- |
| 1. Repair foundations | Memory/router fixes with focused regression coverage | Existing tests remain green; K-01 through K-04 pass; multi-instance ownership, malformed responses, finite limits and stop integration verified. |
| 2. Local fleet | Bounded planning/review loop and evidence ledger | Real selected local-model smoke test recorded; budgets, cancellation, absent models and crash recovery tested; no external tools enabled. |
| 3. HeyPCB adapter | Authenticated live-schema discovery and guarded proposals | Missing auth and offline schemas fail clearly; mock transport tests pass; no-charge policy and project/argument approval checks verified before any permitted live call. |
| 4. Mac release | Reproducible isolated build and operator CLI | Node linkage, unit/integration/build/smoke checks and dependency audits recorded on macOS; clean rollback; no false full-fleet success banner. |

The required regression matrix includes cross-owner denial/audit, concurrent ownership, expired approvals, replayed approvals, forged model identity, prompt-injection text as data, malformed tool results, unknown-cost operations, changed schemas, rate limits, redirect attempts, symlink exports, stop during dispatch, and unavailable providers. Separate mock transport tests from genuine provider and HeyPCB smoke tests. Do not assert test counts before executing the resulting suite.

Suggested operator surfaces are doctor, inventory, plan, approve, run, status and stop. These names describe the proposed interface; they are not available commands yet. Hardware part selection, board dimensions, manufacturing, biological devices and physical actuation remain outside this release.

## 11. Review state and provenance

The prior in-chat integration scope is carried forward here. This is the written architectural specification for review, not an executable implementation plan or a release approval. After review, prepare the implementation plan and choose the execution method. Do not merge dependency branches or launch a service merely because this design is published.

Primary project sources:

- [BioChip memory core](https://github.com/sonoxo/gpt-doug-llm/blob/a09ae92e61c5ea389e5fa774bbffebde669f90e7/biochip/core.py)
- [Local model router](https://github.com/sonoxo/gpt-doug-llm/blob/a09ae92e61c5ea389e5fa774bbffebde669f90e7/biochip/models.py)
- [Existing MCP transport](https://github.com/sonoxo/gpt-doug-llm/blob/82cfbf6f741b26b8a614e236ea1182a18d7285d6/xunia_godis.py)
- [Existing cooperative stop gate](https://github.com/sonoxo/gpt-doug-llm/blob/82cfbf6f741b26b8a614e236ea1182a18d7285d6/ai_killswitch.py)
- [HeyPCB fork README, authentication and billing](https://github.com/sonoxo/heypcb-mcp/blob/ca2d97c41515c2a7c045d75f7882cfb3bac1eb43/README.md)
- [Python urllib default redirect handling](https://docs.python.org/3.11/library/urllib.request.html)
- [MCP annotation trust limitations](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/)
