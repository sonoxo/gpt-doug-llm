# GPT-Doug-Shaggoth Autonomous Factory

**Project:** `sonoxo/gpt-doug-llm`  
**Mode:** Local, bounded, review-gated drafting. **No deployed agent swarm, no unlimited compute, and no credential harvesting.**

## What actually works

A Python-standard-library server accepts scoped local tasks and moves them through a persistent SQLite queue using one worker thread. Five conceptual specialists map onto executable stages:

| Stage | Component | Implemented operation |
| --- | --- | --- |
| Plan | GPT-Doug | Validate scope and generate acceptance contract |
| Build | GPT-Shaggoth | Write an offline scaffold, evidence brief or test plan; optional locally hosted Ollama code draft |
| Verify | GPT-Pineal | Parse Python AST without execution, check filenames, secrets and exact SHA-256 file digests |
| Critique | GPT-Chaos | Record caveats about execution, uncertainty and safety; generate review artifact |
| Review | GPT-Redpanda | Hold output for human approval or rejection; never publish or deploy automatically |

Stages run automatically **only while the factory process is running**. A job is **not** claimed to be an implemented feature just because a scaffold compiles. All generated code requires independent human review and testing before any execution. The SQLite record and output bundles persist across restarts. This system does not launch the five existing component runtimes; their names describe governed workflow responsibilities.

## One-command start (macOS / Linux)

From your checked-out GPT-Doug-Shaggoth factory branch:

```sh
bash run-GPT-Doug-Shaggoth-Factory.command
```

Your browser opens at **http://127.0.0.1:8772/**. The launcher seeds three idempotent local sample jobs and uses the canonical repository guardrail source. Stop the process with `Ctrl+C`. A launcher started from another directory resolves its own path.

Alternative:

```sh
bash scripts/doug-max shaggoth-factory
```

If the browser doesn't automatically open, manually visit the printed loopback URL. The server intentionally refuses non-loopback listeners, remote origins and unauthorized mutation requests. It is not publicly deployed.

## CLI and offline validation

No API key, subscription, AWS, cloud account or pip package is required for the default offline engine.

```sh
python3 gpt_zyra_shaggoth/factory.py status
python3 gpt_zyra_shaggoth/factory.py demo
python3 gpt_zyra_shaggoth/factory.py enqueue --kind python-scaffold --goal 'Draft a local data normalization utility'
python3 gpt_zyra_shaggoth/factory.py work --max-jobs 5
python3 -m unittest discover -s tests -p 'test_shaggoth_factory.py' -v
```

The data directory defaults to `~/.gpt-doug/shaggoth-factory` and is private (0700); the SQLite ledger and generated files are 0600 where POSIX permissions apply. If the canonical policy cannot be verified, normal production **fails closed**.

## Standalone demo distribution

The standalone ZIP intentionally contains no copied/forged canonical project policy. It runs the same factory under an **explicit `--demo-policy`** flag and reports `DEMO_ONLY` with zero canonical rules confirmed. In this mode only bounded local/offline drafts are allowed. This shows the actual pipeline and artifacts without implying repository permissions or a live Shaggoth agent process.

## Local Ollama (optional)

For real locally generated code proposals instead of deterministic scaffolds, start the user-installed Ollama application separately, download a compatible model using Ollama's official tools, and choose an installed model. Then from **the trusted repository checkout** run:

```sh
python3 gpt_zyra_shaggoth/factory.py --allow-ollama --model qwen2.5-coder:1.5b serve --demo
```

The factory only contacts `http://127.0.0.1:11434/api/generate`, with a fixed host, timeout, disabled proxies and redirects, and bounded input/output lengths. This mode is opt-in, and will not work in `DEMO_ONLY`. It **does not** run the generated code. The verifier parses the AST and flags unsafe imports and dynamic execution calls; these are preliminary checks, **not** a security sandbox or formal proof of safe code. If the model isn't installed/available, the job is blocked with an auditable failure instead of inventing a result.

## Operational safety and limits

- One local worker and at most **48 pending/active jobs**; history capped at **500 jobs**, task descriptions capped at 480 chars, generated files capped at 32 KiB each.
- Local queue processing is automatic while the terminal/server remains open; no 24/7 cloud process, auto-scaling, self-modification or autonomous code execution.
- Every draft contains `manifest.json`, `verification.json`, `review.json`, `plan.json`, plus blueprint output. ZIP downloads rehash every file and reject tampering.
- Review buttons approve or reject a **local draft record** only. No remote tool actions, deployments, key issuance, repository merges, container commands or shell execution.
- The dashboard uses same-origin CSRF headers, fixed Host and Origin checks, an SSE viewer limit of eight, and restrictive CSP. Access is **local only**, not a general multi-user authentication solution: other trusted local processes could still connect.
- A built-in demo generates reproducible sample drafts, **not** artificial medical research, universal claims, actual AGI or proof of functioning Shaggoth agents.
- Sensitive data should not be pasted into task descriptions; goal text is stored in the user's local database. Credential patterns are rejected but this is not a comprehensive data-loss-prevention scanner.

## How to verify

Run the unit tests. Open the dashboard and submit a test task. Watch the five stages advance, inspect the SQLite-backed audit feed, download a ZIP and compare manifest hashes. Verify that only `AWAITING_REVIEW` drafts expose an approval action; approved records remain local. Start a second browser to observe SSE updates. Kill the server and restart it; historical jobs should remain present.

**Known limitations:** Crash-interrupted processing jobs may require manual requeueing; the first version does not recover in-flight work automatically. Offline blueprints produce reproducible scaffolds/checklists, not arbitrary fulfilled specifications. Local model source proposals are never executed. External deployment is deliberately outside this factory.
