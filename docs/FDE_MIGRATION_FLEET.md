# GPT-DOUG-LLM — AI FDE Migration Fleet

## What changed

GPT-DOUG-LLM now exposes a deterministic migration mission planner in `zyra_control_plane/fde_migration.py` and role-level authorization manifests in `zyra_control_plane/capabilities.py`.

This is a clean-room XUNIA implementation based on public AI FDE migration concepts. It does not contain Palantir proprietary source code, model weights, private APIs, or tenant internals.

## Runtime path

```text
GPT-DOUG CORE
    |
    v
build_migration_plan()
    |
    v
PLAN -> CONNECT -> INTERPRET -> ENHANCE -> STANDARDIZE -> VERIFY -> DEPLOY
                                                        |
                                                        v
                       VERIFY <- RE_RUN <- REPAIR <- DIAGNOSE
                                                        |
                                                        v
                                                  SME ESCALATION
```

## Role manifests

The control plane registers separate agents instead of granting a single migration agent every capability:

- `fde-source-scout`
- `fde-schema-cartographer`
- `fde-code-interpreter`
- `fde-mapping-engineer`
- `fde-transform-builder`
- `fde-verifier`
- `fde-diagnostician`
- `fde-sme-gateway`
- `fde-release-controller`
- `fde-auditor`

`READ_ONLY` can discover/profile/interpret/propose/test where no writes are required. `WRITE_LOCAL` can create branch-local artifacts and evidence but cannot cross an external-effect boundary. Release/promotion requires a grant that explicitly permits network, writes, **and external effects**.

## Model behavior

`models/gpt-xunia-godis/Modelfile` now instructs the orchestrator to:

- use the seven-stage migration pipeline
- provide minimum viable context per role
- separate read/proposal/local-write/test/human/release/audit authority
- cap automatic repair cycles at three by default
- escalate rather than silently widening permissions
- require provenance, versioned transforms, reconciliation/evals, rollback, impact review, and evidence before declaring completion

## Public references

- https://www.youtube.com/watch?v=e90qUUh8_us
- https://www.palantir.com/docs/foundry/ai-fde/overview/
- https://www.palantir.com/docs/foundry/ai-fde/modes-capabilities/
- https://www.palantir.com/assets/xrfr7uokpv1b/2F8L1TTINRFCg8IGhcJ8vo/1965d99b6512cbae17b845ec8d26ebd2/SAP_Migration_Whitepaper.pdf
- https://github.com/s-andthat/palantir-ai-fde-library — MIT community reference

## Example

```python
from zyra_control_plane import build_migration_plan

plan = build_migration_plan(
    "Migrate legacy ERP schema and business logic into the XUNIA ontology",
    ["database", "source-code", "pdf", "spreadsheet"],
)

print(plan.to_dict())
```

The returned object is a plan/authority contract. Tool execution still belongs to the surrounding runtime and must satisfy its capability grant and approval policy.
