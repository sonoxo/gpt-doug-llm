# GPT-DOUG / ZYRA AI Emergency Stop (Operator-Controlled)

**Safety boundary:** this is a human-initiated, local/distributed **AI execution gate**. It does not confer authority to stop other companies' models or servers. It is not a mechanism for shutting down critical infrastructure, physical safety systems, or life-support services.

## What it does

The STOP latch is stored outside the repository at `~/.gpt-doug/ai-killswitch/STOP` (or the operator-managed `GPT_DOUG_AI_STOP_DIR` directory). A second operator-level `GPT_DOUG_AI_BLOCK_ALL=1` configuration forces the gate closed even if no STOP file is present. Both are checked afresh at AI action boundaries, rather than cached. A malformed stop configuration, unreadable state, or a symlinked latch causes an execution denial. An interactive terminal is required to rearm the local file latch; a forced environment stop cannot be rearmed through the CLI. Stop is idempotent, persistent across model/process restarts, and records a best-effort local operator audit log.

## The operator phrase: STOP THE KRAKEN

The exact operator **activation command** is:

```bash
gpt-doug-llm stop the kraken
```

Install the command from the repository root in a trusted local environment:

```bash
python3 -m pip install -e .
```

The fallback for a source checkout that has not been installed is:

```bash
python3 -m ai_killswitch stop the kraken
```

The parser recognizes only the exact command tokens, case-insensitively. An explanatory sentence, prompt, email, log, or model-generated text **must not** be interpreted as an operator request to trigger a stop. **This phrase is not a secret or an authorization credential.** OS operator permissions and deployment controls must protect the switch from untrusted users. This command only **activates** the stop; it cannot clear, rearm or bypass it.

This GitHub implementation does not activate itself based on text appearing in a conversation. The operator must explicitly run the CLI on a host where the code is installed, or invoke an appropriately authenticated operator control that executes the same local stop operation. Merely creating a PR or saying the phrase in chat is not evidence that any running AI has been stopped.

## Commands (on an owned system)

```bash
python3 -m ai_killswitch status
python3 -m ai_killswitch stop --reason "operator emergency shutdown"
python3 -m ai_killswitch check  # exit code 3 when blocked
python3 -m ai_killswitch resume  # requires interactive local confirmation
```

For shared containers, mount an **operator-owned** stop directory (same path/volume across all protected runtimes) and set `GPT_DOUG_AI_STOP_DIR` consistently. For an immediately forced deployment block, set `GPT_DOUG_AI_BLOCK_ALL=1` using a host/deployment secret/configuration service that agents cannot edit. Never store a stop-state file in a model-writable workspace. AI service identities should have **read** permission to the operator-owned STOP state, not delete/rearm permission. The stop CLI must run as the authorized operator identity in that environment.

## Strict deployment mode: fail closed if the STOP mount disappears

Default local development remains backwards-compatible: the missing state directory is
interpreted as "never initialized." This is **not suitable for a critical deployment**
where a lost or unmounted stop volume could otherwise allow AI work to resume.

For each controlled host, the **human operator** first provisions an absolute,
operator-owned STOP directory and ensures it is visible inside each AI worker.
The service identity should only be able to **read**, not rearm or alter it.

```bash
install -d -m 700 "$HOME/.gpt-doug/ai-killswitch"
export GPT_DOUG_AI_STOP_DIR="$HOME/.gpt-doug/ai-killswitch"
export GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY=1
gpt-doug-llm status
```

The example is for a single-user local machine. For containers or multi-user services,
use an **operator-owned mount** and grant workers read/traverse access (never write/delete
access), instead of relying on the local `700` mode above. Place the two environment
variables in the actual service or container configuration, **not only in an operator's
shell**. Ensure every protected worker receives the same absolute in-container path.

When strict mode is set:
- Missing, unreadable, symlinked, or non-directory STOP state => block AI execution.
- Existing valid operator state without STOP => permit already-authorized work.
- Presence of STOP => deny new AI execution until explicitly rearmed.
- If the mounted state disappears while STOP was engaged => remain blocked.
- Interactive rearm refuses to silently recreate an absent required state directory.
- Invalid strict-mode configuration or relative configured paths => fail closed.

`GPT_DOUG_AI_BLOCK_ALL=1` remains the stronger independent host stop flag.
Strict mode does **not** prevent a privileged administrator from tampering with
the state, or let Python control unrelated AI services. Production enforcement
requires host-controlled firewall/network egress rules, model credential disablement,
and independent physical safety controls where relevant.

## Enforced paths in this change

- Shared Python `ai_killswitch.require_ai_allowed`: default gate for connected Python services.
- `agents.llm_backend`: all facade chat calls; outbound provider transport and stream output checks; OpenAI, Anthropic, Gemini, Ollama, auto, Astra, XUNIA routes.
- `agents.xunia_stream`: provider streaming HTTP transport checks.
- `gpt_brain.kernel` (including injected chat functions): agent dispatch and provider calls.
- `agents.agent_chain`: task start and model-call dispatch.
- `zyra_control_plane.control_plane`: mission starts and each DAG step.
- `wakeup3lm.runtime`: governed IDE tool execution.
- `gpt_zyra_shaggoth.factory`: new jobs and cooperative stage boundaries.
- `workers/agent-daemon.py`: queue suppression while STOP is engaged and supervised termination of an owned Claude subprocess if STOP is activated while executing.
- `local-control/gpt-doug-local-control`: existing local PANIC triggers the ecosystem latch; clearing local panic **does not** rearm AI.

## Limitations / non-negotiable external controls

1. **No global Internet-wide stop.** External models, organizations, products, devices, and unrelated repositories are not under this switch.
2. **Not every existing subprocess/service is wired.** Independent Node/TypeScript apps, external SDK clients, third-party binaries, previously deployed service versions, scheduled cloud agents, and separate Sonoxo repositories must adopt the same gate or be blocked at the operator's gateway. Green unit tests for integrated paths are not an audit of every possible AI entry point.
3. **In-flight requests:** gate checks happen at entry and cooperative checkpoints. Blocking new connections and cancelling *all* in-flight requests requires provider cancellation plus OS/network controls. A blocked response does not prove the external model stopped computing.
4. **Separate machines:** STOP is per host/path unless the operator explicitly deploys a shared, highly available state source with authenticated propagation. Failing over to a disconnected host can otherwise bypass the file latch. For strict containment, disable model-service identities, revoke API credentials, pause deployment/schedulers, and block model-provider egress at a **separate host-controlled firewall/service mesh**.
5. **Operator identity:** an interactive confirmation is a safeguard against accidental rearm, not cryptographic proof of a human. Protect the latch through filesystem ACLs, IAM, separate privileges, and independent operator confirmation. Malicious code with operator permissions can tamper with any Python-only check.
6. **Physical safety:** never rely on this Python gate as the only emergency stop for robots, UAVs, healthcare devices, industrial PLCs, or other hazardous machinery. Use independent hardware safety circuits with manual override and deterministic safe-state transitions.

## Verification

```bash
python3 -m unittest tests.test_ai_killswitch -v
python3 -m unittest tests.test_ai_killswitch_integrations -v
python3 -m py_compile ai_killswitch.py
```

**Acceptance:** STOP prevents model/chat dispatch, new autonomous jobs, and new mission/IDE actions; stops a supervised Claude subprocess; persists across process restarts; cannot be cleared by an automated noninteractive rearm; reports state while stopped. All pathways outside those checks are explicitly **unverified**.