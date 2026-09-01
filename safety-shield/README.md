# VIRGINIA-LLM — SAFETY SHIELD / GLASS ONION

Defensive governance/control-plane ontology for `virginia-llm` / `gpt-doug-llm`.

## Core rule
**No agent gets ambient authority.** Identity, context, policy, scope, risk, approvals, and audit
must all resolve before a privileged action is executed.

## Glass Onion
The system is observable in layers:

`INTENT → IDENTITY → CONTEXT → POLICY → TOOL → EXECUTION → EVIDENCE → OUTCOME`

Every layer emits an audit event. A later layer cannot silently override an earlier denial.

## 24-agent fleet
See `agents/fleet-24.json`. The fleet includes:
- zero-trust identity + least privilege
- prompt/tool security
- data provenance/privacy/secrets
- Korea AI Basic Act mapping
- NIST AI RMF mapping
- public NSA guidance mapping
- human oversight, transparency, explainability
- red-team testing, incident response, kill switch
- immutable-style audit and release certification

## Regulatory mapping
The control matrix maps current controls to:
- Korea AI Basic Act Articles 31–35
- NIST AI RMF Govern / Map / Measure / Manage
- public NSA guidance on Zero Trust, AI data security, agentic AI, and MCP security

**Important:** `nsa-guidance-mapper` consumes only public cybersecurity guidance. It does not connect to
NSA systems and the project does not claim NSA affiliation, authorization, endorsement, or access.

## Decision pipeline

```text
request
  ↓
identity-warden
  ↓
prompt-injection-sentinel
  ↓
high-impact-classifier
  ↓
model-risk-assessor
  ↓
tool-firewall ────── deny → audit-ledger
  ↓
human-oversight-gate (when required)
  ↓
least-privilege-broker
  ↓
EXECUTE
  ↓
output-integrity-checker
  ↓
transparency-labeler
  ↓
audit-ledger → release-certifier
```

## Summon
The fleet is declared, not granted uncontrolled autonomy. An orchestrator should load
`agents/fleet-24.json`, instantiate each role with scoped capabilities, and route all actions through
`policies/shield.rego`.

## Suggested next implementation
Wire the policy gate into the existing tool/MCP dispatcher and require a signed pre-execution
decision object for every side-effecting action.
