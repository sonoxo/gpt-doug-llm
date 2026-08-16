# GPT Doug LLM — Unified Agentic System

**EUREKA // Build anything // Keep humans in command.**

GPT Doug is a provider-neutral, local-first agentic workspace. It boots safely
without an AI provider and keeps cloud or local providers behind explicit opt-in:

- **gpt-doug-llm** — terminal client, Zyra watchdog, 3FA auth, ASTRAL, EUREKA protocol
- **gpt-doug-web** — web platform, multi-agent chain, LLM backend, crypto store, runner
- **xuniaverse-production/xuni-workers** — agent daemon, ontology, XQE engine, trust dossier
- **gpt-doug-roblox** — Roblox game director persona
- **Modelfile.gpt-freewill** — autonomous engineering agent mode

## Architecture

```
gpt-doug-llm/
├── gpt-doug              # Secure terminal client
├── zyra.py               # Unified watchdog (ZYRA/3.0)
├── compliance.py         # Jurisdiction-aware policy gate
├── auth_gate.py          # Three-factor access (3FA)
├── astral.py             # Two-person high-assurance elevation
├── eureka.py             # Cooperative AI messaging protocol
├── dev_terminal.py       # Constrained EUREKA 369 terminal
├── secret_store.py       # OS-backed secret retrieval (Keychain)
├── foundry_guard.py      # Palantir Foundry governance bridge
├── security_review.py    # Machine-readable review evidence
├── security_text.py      # Unicode normalization for policy checks
│
├── agents/               # Multi-agent chain & LLM backend
│   ├── agent_chain.py    #   Planner → Executor → Reviewer with sub-agent spawning
│   ├── llm_backend.py    #   Provider registry + normalized chat contract
│   ├── ontology.py       #   Task-graph schema (Task → Steps → Artifacts)
│   └── security_text.py  #   Unicode normalization (shared)
│
├── web/                  # Web platform
│   ├── server.py         #   HTTP server + SSE streaming
│   ├── auth.py           #   Single-password gate
│   ├── crypto_store.py   #   At-rest AES encryption for projects
│   ├── runner.py         #   Real project server execution
│   ├── worker.py         #   Autonomous marketplace worker
│   ├── ideas.py           #   Idea/task management
│   ├── users.py          #   User management
│   ├── paid_tasks.py     #   Paid task system
│   ├── stripe_checkout.py #  Stripe payment integration
│   ├── twilio_webhook.py #   Twilio SMS webhook
│   ├── draft_comments.py #   YouTube comment drafting
│   ├── youtube_comment.py #  YouTube comment automation
│   └── *.html / *.js / *.css  # Frontend assets
│
├── workers/              # Background workers
│   ├── agent-daemon.py   #   Task queue daemon (watches tasks/*.json)
│   ├── zyra_guard.py     #   Pipeline-specific guard (RICE + classification)
│   ├── ontology_workers.py #  Foundry-inspired ontology (objects, links, actions)
│   ├── web_ui.py         #   Minimal web front end for the daemon
│   ├── xqe.py            #   XQE reasoning pipeline (Superposition → Collapse)
│   ├── trust_dossier.py  #   Security posture report generator
│   └── twilio_calling.py #   Outbound calling via Twilio Voice API
│
├── models/               # Ollama Modelfiles
│   ├── Modelfile         #   Base GPT Doug (qwen2.5-coder:7b)
│   ├── Modelfile.gpt-freewill  #  Autonomous engineering agent
│   └── AGENTS.md         #   Roblox game director persona
│
└── tests/                # Unified test suite (55 tests)
    ├── test_zyra.py             #   Core Zyra tests
    ├── test_zyra_unified.py     #   RICE signals + classification tests
    ├── test_zyra_guard.py        #   Attack/evasion regression suite
    ├── test_eureka.py            #   EUREKA protocol tests
    ├── test_auth_gate.py         #   3FA authentication tests
    ├── test_astral.py            #   ASTRAL two-person control tests
    ├── test_compliance.py        #   Compliance gate tests
    ├── test_dev_terminal.py      #   Dev terminal tests
    ├── test_foundry_guard.py     #   Foundry bridge tests
    ├── test_agent_daemon.py      #   Agent daemon tests
    ├── test_ontology_workers.py  #   Ontology regression suite
    └── test_dev_terminal.py      #   Dev terminal tests
```

## Zyra 3.0 — Unified Watchdog

Zyra is the deterministic defense-in-depth layer. Version 3.0 merges:

- **HMAC audit chain** (from gpt-doug-llm) — tamper-evident, fail-closed logging
- **Secret redaction** (from gpt-doug-llm) — API keys, private keys, credentials
- **Block patterns** (from gpt-doug-llm) — destructive commands, prompt injection
- **RICE social-engineering signals** (from xuni-workers) — Reward/Ideology/Coercion/Ego detection
- **Classification taxonomy** (from xuni-workers) — UNCLASSIFIED through TOP_SECRET
- **Thread-safe logging** (from xuni-workers) — lock-protected audit writes
- **`review()` interface** (from xuni-workers) — dict-return compatibility for the daemon

Zyra does not replace OS sandboxing, least-privilege, dependency scanning, or professional review.

## Quick Start

### Main Web Interface

```bash
export GPT_DOUG_PROVIDER=none
export DOUG_ACCESS_PASSWORD="choose-a-local-password"
python3 web/server.py
# http://localhost:8787
```

The autonomous marketplace worker is disabled by default. Enable it deliberately
with `GPT_DOUG_ENABLE_WORKER=true`.

### Terminal Client

```bash
# Select none (default), gemini, openai, or the optional legacy ollama provider.
export GPT_DOUG_PROVIDER=none

# Set up 3FA environment
export GPT_DOUG_VERIFIED_BUSINESS_EMAIL="builder@example.com"
export GPT_DOUG_ALLOWED_EMAIL_DOMAINS="example.com"
export GPT_DOUG_VERIFIED_PHONE="+12125550123"
export GPT_DOUG_JURISDICTION="US-NY"

# Launch
./gpt-doug
```

### Agent Daemon

```bash
# Drop a task file
echo '{"id": "task-1", "prompt": "build a REST API"}' > workers/tasks/task-1.json

# Run the daemon
python3 workers/agent-daemon.py
```

### FreeWill Autonomous Mode

```bash
ollama create gpt-freewill -f models/Modelfile.gpt-freewill
```

### Run Tests

```bash
python3 -m pytest tests/ -v
```

## Commands

- `/help` — show commands
- `/clear` — clear conversation memory
- `/mission` — display the operating principles
- `/zyra` — show watchdog status
- `/compliance` — show declared compliance context
- `/deepthink` — toggle deep think mode (draft → self-critique → revise)
- `/eureka 369` — request constrained developer session
- `/quit` — exit

## Principles

1. Build useful things.
2. Explain important decisions.
3. Protect user data.
4. Ask before destructive or external actions.
5. Keep humans in command.

## License

MIT. GPT Doug is an independent open-source project.


## Security

See [SECURITY.md](SECURITY.md) for the security policy, vulnerability reporting process, and known limitations.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR process.

## Disclaimer

GPT Doug is an independent open-source project. All knowledge base entries are from public sources, properly attributed. No government entity (CIA, FBI, NSA) or corporation (IBM, MIT) has reviewed, endorsed, or authorized this software. Palantir Foundry references are pattern-inspired, not connected to any live Foundry tenant or API. Zyra is a keyword/pattern guard, not a semantic security system. OS-level sandboxing, least-privilege, and professional security review are still required.
