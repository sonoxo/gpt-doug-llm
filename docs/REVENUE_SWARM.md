# Sonoxo Revenue Swarm

The revenue swarm is a bounded multi-agent orchestration layer for Sonoxo / GPT-Doug. It parallelizes independent prospect pipelines while keeping each prospect's own stages ordered.

Pipeline:

scout -> qualify -> match -> proposal -> outreach_draft -> qa

The implementation lives in workers/revenue_swarm.py.

## What it does

- Runs multiple prospect pipelines concurrently.
- Uses the existing GPT-Doug agent chain for each specialized role.
- Deduplicates prospects before dispatch.
- Persists stage-level audit records and aggregate metrics.
- Detects the active model provider and reduces concurrency for a local Ollama runtime.
- Marks outreach drafts as approval-required.
- Does not send messages, purchase anything, or move money.

The rule name for aggressive bounded scaling is:

ForeverRuleGPTDOUGLLMMAXMIMIXK

## Quick start

Synthetic demo:

    python3 workers/revenue_swarm.py --demo --workers 32

JSON array input:

    python3 workers/revenue_swarm.py --input prospects.json --workers 32

JSONL input:

    python3 workers/revenue_swarm.py --input prospects.jsonl --workers 32

Each prospect may contain:

    {
      "prospect_id": "optional-stable-id",
      "name": "Decision maker",
      "organization": "Company",
      "pain": "Known operational pain",
      "budget_signal": "Known purchasing signal",
      "channel": "source or channel",
      "context": "evidence and notes"
    }

## Concurrency

Environment controls:

- GPT_DOUG_SWARM_WORKERS: requested worker count, default 32.
- GPT_DOUG_SWARM_HARD_MAX: absolute process-side cap, default 64.
- GPT_DOUG_SWARM_LOCAL_CAP: cap when the detected provider is Ollama, default 2.

The active worker count is:

    min(requested_workers, hard_max_workers)

For Ollama it is additionally clamped to GPT_DOUG_SWARM_LOCAL_CAP. This lets cloud-capable deployments scale while protecting a single local model server from overload.

## Audit and metrics

When persistence is enabled, the swarm writes:

- workers/live/revenue-swarm.jsonl
- workers/live/revenue-swarm-metrics.json

Metrics include:

- requested versus active workers
- provider
- prospects received
- unique and deduplicated prospects
- completed pipelines
- successful and failed stages
- drafts awaiting approval
- elapsed runtime

## External actions

The swarm deliberately stops at draft generation. A separate authorized connector layer can take an approved draft and send it, but that external action must remain explicit and auditable. The same rule applies to live payment or payout actions.

Stripe checkout links, CRM credentials, mail credentials, API secrets, and bank data should be supplied through environment variables or a secrets manager. Do not commit them to the repository.

## Testing

Run:

    pytest -q tests/test_revenue_swarm.py

The test suite uses a fake runner, so it does not call an LLM, send outreach, or touch Stripe.
