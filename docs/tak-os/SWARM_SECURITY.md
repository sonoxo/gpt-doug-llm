# GPT-Doug × GPT-Chaos — Phase 2 Swarm Security & Operator Runbook

**Implementation type:** six **deterministic** virtual reviewers and an explicitly opt-in **local Ollama advisory**. The name GPT-Chaos does not imply any new OpenAI model, independent artificial intelligence, hidden runtime, worldwide computer access, or government endorsement.

## Local-only data flow

```text
Synthetic browser entity / local CoT event (DEMO-/LAB- only)
             |
    localhost JSON API + session token + origin and Host checks
             |
        SwarmKernel (Python stdlib)
       /   |    |      |       |      \
    Doug Chaos  ZYRA  Ontology Provenance Watchdog   [Ollama advisory?]
       \   |    |      |       |      /               (opt-in, localhost)
        typed proposal + agent votes  <-----------------------|
             |
       SQLite review queue + local SHA-256 chained audit
             |
   EXPLICIT HUMAN APPROVAL (low risk synthetic only)
             |
   CoT 2.0 encode -> existing State.ingest() -> SQLite + SSE map
```

A proposal cannot transmit any packet, execute shell code, spawn agents, access files, publish to GitHub, control a vehicle, or contact TAK infrastructure. Only the existing on-host `State.ingest()` path can modify the **synthetic** local map after review. No connected TAK Server, external network, or remote model is enabled by default.

## Bounded phases and agency

| Role | Phase | Effect |
|---|---|---|
| `gpt-doug-planner` | Schema/plan | Read-only proposal review |
| `gpt-chaos-critic` | Critique | Geographic-region/outlier challenge; never silently accepts outliers |
| `zyra-guardian` | Policy | Denies unbounded execution/real TAK commands |
| `ontology-verifier` | Type verification | Typed synthetic entity and coordinate check |
| `provenance-sentinel` | Evidence origin | Only operator-local synthetic intake |
| `pulse-watchdog` | Resource budget | 30 evaluations/min, 64 pending proposals; every 8 demo ticks audits heartbeat |
| `gpt-chaos-local-llm` (optional) | Advisory | Local 127.0.0.1 Ollama one-line critique; **non-authoritative** |

No model output contributes to the risk gate. If an optional model is missing, slow or untrusted, the rule-based reviewers remain authoritative; no follow-on external action occurs.

## Human control / STOP THE KRAKEN

1. Start the local gateway: `sh start.sh web`. The swarm boots **PAUSED** and never auto-starts after a restart.
2. In **GPT-Chaos Swarm**, press **START SWARM**. This enables review and a bounded read-only heartbeat.
3. Submit a synthetic JSON candidate. The queue stores all votes and explicitly marks status `pending_review`.
4. For **low-risk** proposals only, a human must type **`APPROVE SYNTHETIC PROPOSAL`**. The change then enters the local synthetic CoT event stream. Higher-risk proposals can only be rejected by the single-operator lab.
5. Press **STOP THE KRAKEN** to latch the engine **STOPPED** on disk. New evaluations/approvals are denied even after the process restarts. To re-enable, enter **`REARM LOCAL SWARM`**; the engine returns to **PAUSED**, not running.
6. Download the hash-chained audit JSON from the dashboard. If audit hashes mismatch, new evaluations and approvals fail closed; the stop control remains available.

## Optional free local Ollama advisory (not required)

Install and run the free Ollama runtime yourself (check its own terms, model license and computer requirements), then explicitly choose a **locally installed** model. Example, after obtaining a model:

```sh
# In a separate terminal, install/start the optional Ollama process per official docs.
# ollama pull qwen2.5:1.5b   # example, requires a separate download and disk space
cd docs/tak-os
TAK_OS_LOCAL_CRITIC_MODEL='qwen2.5:1.5b' sh start.sh web
```

The optional critic only calls `http://127.0.0.1:11434/api/generate` through the Python standard library; the host cannot be overridden. It disallows redirects, ignores proxy environment settings, allows a validated local port (`TAK_OS_OLLAMA_PORT`), limits responses to 4 KiB, caps inference at 96 output tokens, and has an 8-second timeout (configurable within 0.5–20 seconds using `TAK_OS_OLLAMA_TIMEOUT`). Requests contain **only normalized fictional entity fields**, not credentials or full event logs. The local model cannot approve/reject or execute anything. The status dashboard distinguishes configured, successful advisory, unavailable and disabled states. The LLM bridge is **not usable from the static GitHub Pages demo** and is not enabled by default. Docker isolates loopback per container; no Docker-to-host Ollama integration is provided.

## Threat model and non-goals

- **Safe input:** Synthetic `DEMO-` / `LAB-` IDs only; bounded JSON; numeric coordinates; four recognized types; no privileged actions or third-party hosts.
- **Tamper evidence:** A local SHA-256 chain covers audit actions; a 2,048-row rolling window maintains a checkpoint anchor. This is **not** an externally notarized signature, cryptographic identity or protection against a malicious administrator who can rewrite the database and checkpoint.
- **Local access:** All browser writes use the loopback gateway's session token, same-origin validation and strict Host checks. The server sends CSP and other security headers. Optional UDP/TCP lab listeners stay on `127.0.0.1` and are disabled by default.
- **Limitations:** This software is not a TAK Server replacement, ATO, certificate-enrollment tool, weapon/vehicle controller, anti-AI global killswitch, network scanner, cloud agent, or a live geospatial intelligence system.
- **Third-party assets:** Map tiles are optional and subject to OSM policy; API and service-worker caches do not include CoT data.
- **Guardrail:** Never use actual device locations, private organizational data, privileged TAK credentials, or government mission material as proposals in the public demo.

## Verification

From the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_tak_os_gateway.py' -v
python3 -m unittest discover -s tests -p 'test_tak_os_swarm.py' -v
python3 -m unittest discover -s tests -p 'test_tak_os_static.py' -v
node --check docs/tak-os/swarm-ui.js
```

Optional browser tests (if Playwright + Chromium are already installed):

```sh
python3 -m unittest discover -s tests -p 'test_tak_os_swarm_browser.py' -v
```

Every workflow uses free, local code or the repository's existing GitHub Actions runner; it does not require a hosted AI token service.
