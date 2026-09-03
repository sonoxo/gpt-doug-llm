# GPT-DOUG-LLM / ZYRA / XUNIA Ecosystem — GitHub Copilot Instructions

You are editing the orchestration and developer-control node of a coordinated ecosystem owned by `sonoxo`.

## Ecosystem map

- `sonoxo/gpt-doug-llm` — orchestration, coding-agent, local-LLM and developer-control layer.
- `sonoxo/zyra` — shared credential/evidence ontology, AI/BI knowledge layer, governance contracts, and ZYRA application services.
- `sonoxo/gods-eye-viewXUNIA` — XUNIA / Glass Onion public-source spatial-intelligence application.
- `RVAI` — reserved ecosystem node. Do not invent a repository or deployment until an actual repository is present or explicitly identified.

Treat these as interoperating sibling projects with explicit contracts. Do not conflate them or silently copy claims/configuration between them.

## Copilot editing authority

When this repository is selected in Copilot Agent/Chat, you may edit implementation code, tests, documentation, workflows, schemas, APIs, configuration, and developer tooling needed to complete the user's requested task. Prefer complete working changes over partial snippets.

You may refactor, repair, harden, document, and extend this repository. When an interface change affects ZYRA or XUNIA / Glass Onion, define the cross-repository contract explicitly and identify the target files or APIs that must change. Do not claim sibling edits occurred unless those repositories were actually edited.

Before declaring completion, run or reason through relevant build, test, type-check, lint, and security validation. Never label a failing gate as passing.

## Shared application pathway

`GPT-DOUG-LLM -> ZYRA -> XUNIA / GLASS ONION -> RVAI`

GPT-DOUG-LLM may orchestrate developer workflows and application-level tasks, but must not bypass authentication, authorization, repository permissions, platform controls, or human approval requirements.

## Engineering rules

- Inspect existing architecture before changing it.
- Reuse existing abstractions and types where sound.
- Prefer deterministic commands, typed interfaces, explicit error handling, and auditable logs.
- Add/update tests for material behavior changes.
- Keep docs synchronized with actual behavior.
- Do not hard-code environment-specific secrets.
- Do not disable failing tests or security gates merely to obtain a green status.
- Never claim deployment/integration success without evidence.

## Security and authorization boundaries

- Never commit secrets, tokens, passwords, cookies, private keys, OAuth credentials, API keys, payment data, or session artifacts.
- Defensive security, authorized testing, public-source analysis, and lab simulation are permitted.
- Do not add unauthorized exploitation, credential theft, persistence, destructive actions, real-world targeting, weapon release, or autonomous lethal functionality.
- Maintain least privilege and human approval for privileged actions.

## Credential/evidence contract

`sonoxo/zyra` is the canonical credential/evidence ontology node. Credential evidence, skills evidence, platform-access evidence, authentication, authorization, governed action, and audit evidence are separate classes.

Do not fabricate credentials, verification IDs, dates, scores, licenses, clearances, government affiliations, customer deployments, third-party permissions, or partner status.

A certificate/badge is evidence, not an access token. Any live platform operation still requires valid authentication and authorization.

## XUNIA / Glass Onion boundary

`sonoxo/gods-eye-viewXUNIA` is the Glass Onion public-source spatial-intelligence application. Preserve evidence-state semantics such as `LIVE`, `DELAYED`, `RECONSTRUCTED`, `MODELED`, `PARTIAL`, and `UNAVAILABLE`. Never promote modeled output to verified live intelligence.

Do not conflate Glass Onion with the separate Navy SBIR repository `sonoxo/xuniahub`.

## Cross-repository handoff

If work in this repository requires a change elsewhere, leave a concise handoff naming:

1. target repository;
2. files/contracts affected;
3. exact interface change;
4. compatibility/security impact;
5. required validation.

The goal is controlled multi-repository evolution with traceable contracts.
