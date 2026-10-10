# GPT-Doug-Chaos // Live Access Rubik Cube

This is a **working real-time, local-only telemetry UI** for `sonoxo/gpt-doug-llm`, not a grant of access, universal-law engine, a cloud swarm, or an autonomous runtime. The six Rubik-style faces are governed by server-side, read-only status checks; rotating the cube **never changes policy or privileges**.

## Start

Python 3.9+ only; **no pip dependencies, API keys, paid services or outbound connections.** From the repository root:

```bash
bash run-GPT-Doug-Chaos.command
# If you do not want it to open a browser automatically:
bash run-GPT-Doug-Chaos.command --no-browser
# One machine-readable local snapshot, then exit:
python3 gpt_chaos/live_cube.py snapshot
```

The launcher opens **http://127.0.0.1:8767/**. The Python process must remain running for the stream to be live. Stop it with **Ctrl+C**. The port is configurable with `--port 8768`; the server is **always bound to loopback**, even when the machine has public network interfaces.

The backend pushes updates using Server-Sent Events (SSE) at roughly **two-second intervals**. The browser initially fetches a JSON snapshot and updates cards, counters and a live request-count plot. If the stream disconnects, it displays **RECONNECTING**, not false active status.

## What is real (and what is not)

| Reading | Meaning |
| --- | --- |
| Process uptime, request totals, SSE viewer count | Measured from the actual local server process |
| Source modules | Rechecked every snapshot using a fixed allowlist of known file paths inside the GitHub checkout |
| Governance | A **sample** of 9 required rule values from `safety-shield/ontology/universal-galactic-federation-guardrails-v1.json` is compared to fixed expectations, with a SHA-256 prefix for change detection |
| Access cube | Six informational faces: **identity, scope, consent, policy, resources, audit**; rotating is purely cosmetic |
| Agent runtimes | **Unverified (0)** by default; the file checks do **not** prove that agents are running, healthy, authorized, or connected |
| External infrastructure | Not probed, connected, scanned, or controlled |

This visualization is a **project policy sample, not a replacement for the canonical full guardrail validator**, a legal compliance finding, or a bearer-access control. A missing or drifted policy is marked **UNVERIFIED**; it is not interpreted as approval. The dashboard does not accept capability changes, usernames, requests for keys, or execution commands.

## Security limits

- `ThreadingHTTPServer` binds **only** `127.0.0.1` and refuses unexpected `Host` / cross-origin `Origin` headers, limiting DNS rebinding and browser cross-origin access.
- Only `GET`/`HEAD` routes are served: `/`, `/styles.css`, `/app.js`, `/api/status`, `/api/health`, `/events`. There are **no write routes**; `POST`, `PUT` and `DELETE` return 405.
- A max of **8 concurrent live SSE viewers**, with stream renewal after 70 seconds.
- HTTP body content is allowlisted and generated without user input, repository paths, environment variables, private keys, prompts, medical records, or raw audit logs.
- The policy file is size-capped (128 KiB) and read only when the path stays inside the project without symlinks.
- Audit is **volatile in-memory telemetry**, not a tamper-proof durable log. Nothing is written to disk by this server.
- A local service on loopback is **not authenticated**. Do not forward its port, make it public, or rely on its cube for actual authorization decisions.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_gpt_chaos_live_cube.py' -v
node --check gpt_chaos/live_cube_ui/app.js
```

The tests launch a real local HTTP server, inspect the SSE stream, check access restrictions and source/policy-state transitions, and run the launcher from another working directory. No network connection is made to external services.

The architecture builds on the existing `gpt_chaos` runtime, ZYRA Shaggoth bridge, Bio-Gpt, and Cure Swarm **as source provenance only**. These agents are not automatically imported or started. To integrate genuine running-process health in a later revision, use explicitly authorized local health endpoints with independently verified identity—never infer execution from a source file.
