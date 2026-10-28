# Devin Enterprise integration

**Status:** proposed adapter; not connected or deployed by this commit.

This integration makes Devin a bounded engineering worker under GPT-DOUG-LLM, rather than a system authority. The canonical ontology, repository permissions, policy checks, and human review remain in GPT-DOUG-LLM/GitHub.

## Responsibilities

- Submit an explicitly approved engineering task to Devin's session API.
- Require a scoped task description and acceptance criteria.
- Keep credentials in environment variables; never commit API keys.
- Return the provider response for review; do not merge, deploy, or grant repository access automatically.
- Keep provider-specific session IDs linked to canonical ontology IDs.

## Configuration

- `DEVIN_API_KEY`: API credential supplied by an authorized administrator.
- `DEVIN_API_BASE_URL`: optional API base URL; defaults to `https://api.devin.ai/v1`.
- `DEVIN_API_PATH`: optional session path; defaults to `/sessions`.

Confirm the current API path, payload schema, and authentication requirements against the Devin documentation for your account before enabling this adapter. The endpoint and payload may vary by API version or enterprise configuration.

## Example

From the repository root, after reviewing the provider's current API docs and installing Python 3.10+:

```bash
export DEVIN_API_KEY='…'
python integrations/devin-enterprise/adapter.py \
  --title "Add regression tests for module X" \
  --prompt "Implement only the scoped task. Acceptance criteria: …"
```

The adapter submits a session request and prints the response. It does not run code locally, inspect private repositories, or merge/deploy changes.

## Required gates before production

1. Verify API endpoint/schema with Devin's current documentation.
2. Use a dedicated service identity with least-privilege access.
3. Run tasks in an approved isolated environment.
4. Require CI, security scanning, and human review before merge.
5. Record task ID, provider session ID, repository/branch, acceptance criteria, test evidence, reviewer, and final disposition in the ontology.
6. Treat all model output and repository content as untrusted input; never expose production secrets to an agent task.

## Canonical ontology mapping

See `ontology.json` and `manifest.json`. This is an integration contract, not proof of a live Devin connection.
