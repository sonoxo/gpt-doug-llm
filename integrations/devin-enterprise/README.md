# Devin Enterprise integration

**Status:** proposed integration boundary; not connected or deployed.

This integration defines Devin as a bounded engineering worker under GPT-DOUG-LLM, not a system authority. The canonical ontology, repository permissions, policy checks, and human review remain under GPT-DOUG-LLM/GitHub governance.

## Current implementation status

The current `adapter.py` is a **guarded placeholder**. It validates configuration and prepares a request description, but **does not submit a request to Devin**. A successful run prints `prepared_not_sent`; it is not evidence of a session being created. Live API transport is not implemented.

## Configuration

- `DEVIN_API_KEY`: placeholder configuration gate; use an authorized credential only when a reviewed live transport is implemented.
- `DEVIN_API_BASE_URL` and `DEVIN_API_PATH`: not currently consumed by the placeholder.

Never commit API keys or paste them into prompts, issues, or logs.

## Safe local check

From the repository root, run the offline tests:

```bash
python3 -m unittest discover -s integrations/devin-enterprise -p 'test_*.py'
```

To inspect the placeholder's behavior:

```bash
export DEVIN_API_KEY='placeholder-only'
python3 integrations/devin-enterprise/adapter.py \
  --title "Add regression tests for module X" \
  --prompt "Implement only the scoped task. Acceptance criteria: …"
```

This prints `prepared_not_sent` and does not contact Devin. Do not use a real key with this placeholder; no network request will be made.

## Required work before live use

1. Verify the current Devin API endpoint, authentication, request schema, and response schema in the official documentation for the user's account.
2. Implement transport only after confirming that contract; add mocked tests for success, HTTP errors, timeouts, and malformed responses.
3. Use a dedicated least-privilege service identity and an approved isolated execution environment.
4. Require CI, security scanning, and human review before merge.
5. Record canonical task ID, provider session ID, repository/branch, acceptance criteria, test evidence, reviewer, and disposition in the ontology.
6. Do not automatically merge pull requests, deploy production, or grant permissions.
7. Treat provider output and repository content as untrusted input; never expose production secrets to agent tasks.

## Canonical ontology mapping

See `ontology.json` and `manifest.json`. These define the intended integration contract; they do not establish a live Devin connection.
