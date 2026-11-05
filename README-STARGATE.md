# UNIVERSAL STARGATE // SI

A real, **free, local-first gateway** for *superintelligence research workflows*, **not** a model claiming achieved superintelligence. Built into the GPT-DOUG ecosystem using the existing `gpt_brain.router.BrainRouter` and cooperative `ai_killswitch` control plane.

## On your Mac

Ollama API port: **11434**. Stargate web UI: **8799**. Different services. If `ollama serve` reports “address already in use,” inspect the already-running service with `curl -fsS http://127.0.0.1:11434/api/tags` rather than trying to launch a second instance.

From the full `sonoxo/gpt-doug-llm` checkout on this branch:

```bash
brew install ollama # only if not already installed
ollama pull qwen2.5:3b
python3 -m universal_stargate
```

Open <http://127.0.0.1:8799/> and keep Terminal open. **No paid API key** is needed. Alternatively install editable from repo root: `python3 -m pip install -e .` then run `gpt-doug-stargate`.

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /` | Interactive single-page operations console |
| `GET /api/status` | Operator emergency-stop state |
| `GET /api/ontology` | Typed conceptual ecosystem graph; explicit connection status |
| `GET /api/policy` | Restrictive THEGREENHOUSE control policy |
| `GET /api/models` | Fixed, read-only local Ollama model inventory |
| `POST /api/route` | Advisory role selection via GPT-DOUG BrainRouter (no execution) |
| `POST /api/chat` | Bounded chat with an *installed* local Ollama model |

## Guardrails

- HTTP server **only binds 127.0.0.1**; Host and POST Origin are checked; no public tunneling.
- Model endpoint fixed to `127.0.0.1:11434`; no arbitrary URLs, third-party API calls, or secret keys.
- Input validation, model allowlist, two concurrent inference requests maximum, structured error handling, no persistent prompts.
- `ai_killswitch.require_ai_allowed` evaluated before inference **and before reply delivery**.
- No external commands, tool execution, repository mutation, self-replication, uncontrolled agents, approval bypass, or actual SI claim.
- Status graph distinguishes wired local components from ontology-only references. Real XUNIA/ZYRA/Fleet integrations are future, operator-approved work.

## Verification

```bash
python3 -m unittest tests.test_universal_stargate -v
python3 -m compileall -q universal_stargate
```

The unit tests use mocked Ollama, so passing tests do **not** imply local inference has been verified on another device.
