# America's AI Action Plan Engineering Profile

GPT-Doug-LLM includes an optional provider-neutral engineering profile derived from the July 2025 White House document **America's AI Action Plan**. The source plan is public policy; this repository translates selected themes into practical software-engineering defaults.

This feature does **not** claim White House, U.S. Government, NIST, DOD, intelligence-community, or other agency endorsement, affiliation, certification, or compliance.

## Runtime behavior

The profile is enabled by default and can be disabled with:

```bash
GPT_DOUG_AI_ACTION_PLAN=0
```

When enabled, `agents.llm_backend` injects the profile once at the provider-neutral chat gateway. That means the same engineering defaults apply to supported OpenAI, Anthropic, Gemini, Ollama, Auto, and XUNIA execution paths that use the gateway.

The `Modelfile` also carries equivalent defaults for direct local-model sessions that bypass the Python gateway.

## Translation from policy themes to engineering controls

### Pillar I — Accelerate AI Innovation

- Prefer open-source/open-weight and local-first options when they satisfy the task.
- Convert ideas into prototypes, working integrations, documentation, and measurable workflows.
- Teach skills and tradeoffs so people can operate and improve the system.
- Require evaluations and explicit success criteria instead of unsupported completion claims.
- Favor inspectable plans, bounded recursion, provenance, interpretability, and robustness.

### Pillar II — Build AI Infrastructure

- Use secure-by-design defaults: least privilege, secret hygiene, dependency integrity, validation, logs, and safe failure modes.
- Build observability, health checks, audit trails, rollback paths, and bounded incident response into production work.
- Prefer efficient available compute and avoid runaway loops or unnecessary resource use.

### Pillar III — International AI Diplomacy and Security

For a general-purpose open-source model, this becomes a technology-protection and model-risk layer rather than geopolitical advocacy:

- Validate model, retrieval, plugin, tool, and external-data outputs before consequential use.
- Protect credentials, private data, repositories, model artifacts, and software supply chains.
- Keep security claims evidence-based and never imply government authority.

## Safety and neutrality boundary

The profile is an engineering configuration, not a political persuasion layer. It explicitly preserves the repository's existing security, privacy, civil-liberties, provenance, human-oversight, and intelligence-compliance constraints.

Policy framing must remain distinct from verified technical facts. High-impact external actions still require appropriate authorization and human review.

## Verification

`agents/tests/test_ai_action_plan.py` verifies:

- all three operational pillars are represented;
- injection is idempotent;
- user messages are preserved;
- the profile can be disabled;
- security and human-control language remains present;
- evaluation, incident response, and secure-by-design capabilities remain part of the profile.
