# XUNIA / GPT-DOUG — Universal RSI Watchtower V1

Provider-neutral, **local-first oversight gateway** for explicitly registered and instrumented AI runtimes. Designed as an additive layer alongside the existing `zyra.py` policy inspection and `ai_killswitch.py` emergency gate.

**Truth boundary:** The term *universal* describes the accepted event schema, not unrestricted control of unrelated providers. This software can enforce actions only when the authorized runtime calls its gate before execution or runs behind an operator-managed interception point. The public web exhibit is synthetic-only and has no model-provider keys. This is a prototype, not an externally assessed high-assurance control plane.

## Run in 1 command — free, no cloud keys

From the GPT-Doug repository root with Python **3.11+**:

```bash
python3 -m universal_watchdog serve
```

Open `http://127.0.0.1:8877/`. The terminal prints an **operator token**, stored in `~/.gpt-doug/watchtower/credentials.json` (0600). In the app, choose **Local live gateway**, enter the operator token, and register a model. Registration returns a separate **model ingest token exactly once**, so one model cannot impersonate another. The operator token is stored in the private local credentials file; each model ingest token is returned once and only its SHA-256 hash is retained in the registry.

Public standalone training dashboard: `docs/watchtower/index.html` or `https://xunia.org/watchtower/` after verified publication. No user registration, external dependencies, or provider network calls needed for its synthetic examples.

## Architecture

| Component | What it enforces | Boundary |
|---|---|---|
| HTTP ingress | Bearer credentials by model and operator | Loopback-only server; use a separate authenticated TLS proxy for remote clients |
| Model registry | Model ID, provider, agent ID, allowed scopes and capabilities | Operator registration required; no implicit discovery or global surveillance |
| Policy evaluator | Known kind/action vocabulary; deny unknown; risk tier, grants, scope, cost and token budgets | Deterministic signatures, not a comprehensive ML classifier |
| RSI change gate | Human approval, SHA-256 test-report identifier, rollback reference, one-use exact-digest permit | External CI/evidence verification is the human operator's responsibility |
| Emergency stop | Local persistent latch + existing `ai_killswitch.status()` where present | Cooperating runtimes only; hardware/host shutdown requires independent controls |
| Audit ledger | SQLite WAL, keyed HMAC event chain, privacy-protecting content HMAC fingerprints | Tail truncation and key/database-owner compromise need off-host immutable attestations |
| API and dashboard | `GET` readout and explicit authenticated operator operations | Public GitHub Pages mode is non-operational simulation |

## Model event schema

Any provider (OpenAI-compatible, Gemini, Claude, Ollama, llama.cpp, vLLM, custom/open-weight, rules-based agents, etc.) can use the same **local policy gate**. A standard-library `WatchtowerClient` class (`universal_watchdog/client.py`) wraps arbitrary Python callbacks and refuses execution on a denied or unreachable gateway. `otel_observation()` maps basic OpenTelemetry GenAI span metadata into privacy-preserving event records. A provider name is descriptive metadata, not an external API connection.

```json
{
  "model_id": "llama3:8b",
  "provider": "ollama",
  "agent_id": "approved-agent",
  "kind": "model_update",
  "action": "self_modify",
  "scope": "public",
  "resource": "repo:staging-branch",
  "source_trust": "trusted",
  "content": "Proposed change summary - never send secrets",
  "test_report_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "rollback_ref": "git:previous-stable",
  "estimated_tokens": 300,
  "estimated_cost_usd": 0.01,
  "trace_id": "trace-123"
}
```

Only registered capabilities and scopes can proceed. A high-impact request receives `202` with `verdict=review`. The operator uses `POST /api/v1/approve` with an independently reviewed test-evidence SHA-256 and the decision ID. A single re-submission with exactly matching fields and returned `approval_id` can return `200` / `allow`. Modified requests or replays return `403`. A global stop denies all actions before the approval check.

**Fail-closed integration requirement:** Treat every non-`200` outcome, network failure, or malformed response as *do not execute*. Attach guard calls **before** model invocation and **before every privileged tool execution**. Example: `scripts/watchtower_adapter_example.py`.

### API

- `GET /api/v1/health`: loopback liveness (minimal public details)
- `POST /api/v1/models`: enroll/rotate model token — **operator token**
- `POST /api/v1/evaluate`: model action guard — **that model's ingest token**
- `GET /api/v1/overview`, `/api/v1/events`, `/api/v1/pending`, `/api/v1/approvals`, `/api/v1/ontology`, `/api/v1/audit/verify`: operator token
- `POST /api/v1/approve`, `/api/v1/stop`, `/api/v1/rearm`: operator token

No permissive CORS policy. Credentials must not be put in URLs. Avoid printing payloads or forwarding raw prompts to telemetry sinks.

## Operator CLI

```bash
python3 -m universal_watchdog doctor
python3 -m universal_watchdog stop
python3 -m universal_watchdog rearm  # interactive terminal confirmation
python3 -m universal_watchdog evaluate < event.json  # exits 3 unless allow
```

For local testing, default controls permit at most **100** actions/model/minute, **50,000** estimated tokens/action, and **$20** estimated cost/action. Configure operator policy before real deployment. Calls to outside providers are intentionally not auto-discovered and no background swarm is spawned.

## Verify

```bash
python3 -m unittest tests.test_universal_watchdog -v
python3 -m compileall -q universal_watchdog
node --check docs/watchtower/app.js
python3 tests/browser_smoke.py  # optional Chromium + Playwright development smoke test
```

The repo's Pages release workflow should also test static assets and public page content. **Passing unit/browser tests ≠ continuous oversight, enterprise hardening, autonomous RSI, or military certification.** Deploy with host-managed credentials, independent secret storage, transport-layer security, off-host audit anchoring, isolation, observability, and an operator-owned stop path before using outside a local laboratory.

### Guidance references

- NIST AI RMF and Generative AI Profile: https://www.nist.gov/itl/ai-risk-management-framework
- OWASP Top 10 for LLM and GenAI Applications: https://genai.owasp.org/llm-top-10/
- OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/

Source and model identities are maintained in the XUNIA governance ontology; no unrelated AI runtime is assumed connected.
