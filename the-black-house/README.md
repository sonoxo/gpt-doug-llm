# THE BLACK HOUSE // KERNEL 3.0.0

Canonical governance, ontology, identity, and control-plane root for the Sonoxo agentic ecosystem.

**Phase 3 status:** canonical executable kernel implemented. Consumer bindings exist for VA3LM, Wakeup3lm, XUNIA, ZYRA/Zyra Cloud, and the AIP shared quality plane. Cross-repo ontology drift is fail-closed in `GPT-DOUG-LLM-MAX Full Completion` CI.

## Authority

This directory is the machine-readable global root for ecosystem identity, service registration, agent registration, mission envelopes, ontology contracts, kernel vocabulary, governance boundaries, and control-plane validation.

It does **not** duplicate service implementation. Each registered component remains owned by its source repository and is referenced here by canonical ID and repository contract.

`XuniaDAO` remains the **XUNIAverse domain root**. It is not the global Black House control-plane root. `ZYRA` remains the security/approval/audit execution authority for its registered actions. External platforms remain authoritative for their own credentials, permissions, and tenants.

## Kernel 3.0.0

The executable kernel is defined by:

- `kernel/kernel.manifest.json` — canonical kernel version, object types, relationships, invariants, and consumer bindings.
- `kernel/kernel.schema.json` — machine schema for the kernel manifest.
- `ontology/ontology.schema.json` — canonical ontology vocabulary, locked to kernel `3.0.0`.
- `../scripts/black_house_kernel.py` — executable fail-closed kernel loader and validator.
- `../scripts/validate_black_house.py` — whole-control-plane contract and drift validator.

Canonical object vocabulary includes `Mission`, `Agent`, `Model`, `Repository`, `Service`, `Tool`, `Evidence`, `Decision`, `Approval`, `Action`, `Deployment`, `Incident`, `Policy`, `Artifact`, and related operational objects.

Canonical relationships are:

```text
EXECUTES · USES · PRODUCES · DERIVED_FROM · AUTHORIZES · GOVERNS
DEPLOYED_TO · IMPLEMENTS · RUNS_ON · ROUTES_TO · AUDITS · EVIDENCES
```

Kernel invariants are fail-closed: typed objects, registered relationships, evidence provenance, explicit human approval for consequential mutation, runtime health before GREEN, and no implied external authorization.

## Bound execution planes

| Plane | Kernel binding | Role |
|---|---|---|
| **GPT-DOUG-LLM MAX / Black House** | canonical | planning, orchestration, kernel authority |
| **VA3LM :8088** | `va3lm/src/va3lm/ontology.py` | bounded coding/runtime execution |
| **Wakeup3lm** | `wakeup3lm/ontology.py` | IDE-native object/link execution state |
| **XUNIA** | `sonoxo/xuniadao/.black-house/kernel.json` | XUNIAverse domain ontology + agents |
| **ZYRA / Zyra Cloud** | `sonoxo/zyra/.black-house/kernel.json` | policy, approval, audit, cloud execution |
| **AIP quality plane** | `sonoxo/aip-community-registry-zyra/.black-house/runtime.json` | reusable CI/security quality plane |

## Control flow

```text
MISSION
  ↓
THE BLACK HOUSE KERNEL 3.0.0
  ↓
RVIA ROUTER
  ↓
SHADOW GLASS identity / provenance / policy
  ↓
CANONICAL ONTOLOGY
  ↓
GPT-DOUG-MAX / VIRGINIA / WAKEUP3LM / VA3LM
  ↓
ZYRA approval / security gate
  ↓
XUNIA / NXYZ / ZYRA CLOUD execution
  ↓
GLASS ONION evidence
  ↓
BLACK HOUSE audit / mission record
```

## Canonical files

- `ecosystem.yaml` — root system manifest.
- `registry/repositories.json` — authoritative repository registry.
- `registry/services.json` — runtime/service registry.
- `registry/agents.json` — agent/model execution registry.
- `missions/mission.schema.json` — universal mission envelope.
- `ontology/ontology.schema.json` — canonical object/link vocabulary.
- `kernel/kernel.manifest.json` — executable Phase 3 kernel contract.
- `kernel/kernel.schema.json` — kernel manifest schema.
- `runtime/runtime-contract.json` — runtime health contract.
- `governance/CONTROL-PLANE.md` — execution and authority boundary.

## CI completion contract

`.github/workflows/gpt-doug-max-full-completion.yml` must prove all of the following before Phase 3 reports GREEN:

1. canonical Black House contracts validate;
2. executable kernel self-check passes;
3. Wakeup3lm accepts canonical objects and relationships;
4. VA3LM tests/lint/security/compile pass and port `8088` answers with kernel `3.0.0`;
5. XUNIA builds/tests and its kernel binding passes;
6. ZYRA tests/typecheck/audit/build and its kernel enforcement tests pass;
7. the AIP shared quality plane reports the same kernel version;
8. canonical object and relationship arrays are byte-order coherent across XUNIA and ZYRA;
9. the final verdict fails closed unless every critical plane is GREEN.

## State language

Use only these lifecycle states when reporting system status:

`planned`, `implemented`, `ci_verified`, `deployed`, `platform_access`, `authorized_action`, `third_party_approved`.

Implementation never implies deployment, credentials never imply authorization, and external-platform adapters never imply tenant entitlement.
