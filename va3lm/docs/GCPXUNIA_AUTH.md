# VA3LM GCPXUNIA Auth + Identity

Root: `sonoxo/xuniadao`

VA3LM now models outbound authentication as a centralized brokered flow rather than passing persistent credentials directly to agents.

```text
AgentIdentity
  → SPIFFE identity validation
  → requested-scope evaluation
  → GCPXUNIA Auth Manager
  → provider policy
  → short-lived credential reference
  → DPoP / mTLS binding
  → VIRGINIA policy boundary
  → VA3LM runtime
  → audit evidence
```

## Rules

- Each governed agent has its own identity.
- Shared and long-lived agent credentials are blocked.
- Raw secrets are not returned by the broker contract.
- User-delegated auth is a separate credential mode.
- Requested scopes must fit both the agent identity and provider policy.
- Broad project/org grants require review.
- Runtime and consequential mutations remain human-gated.

## API

- `GET /api/defense/ontology`
- `POST /api/identity/evaluate`
- `POST /api/auth/broker`

## Sources

- Google Cloud IAM: authenticate agents with their own identity.
- Google Cloud IAM: Auth Manager overview.
- Google Cloud Security Community: IAM agent identity/governance material.
- Palantir Ontology public docs: objects, properties, links, actions, functions, dynamic security.

These are architecture references. VA3LM does not claim a live Google Cloud or Palantir deployment unless separate deployment evidence exists.
