# THE BLACK HOUSE

Canonical governance and control-plane root for the Sonoxo agentic ecosystem.

## Authority

This directory is the machine-readable root for ecosystem identity, service registration, agent registration, mission envelopes, ontology contracts, governance boundaries, and control-plane validation.

It does **not** duplicate service implementation. Each registered component remains owned by its source repository and is referenced here by canonical ID and repository URL.

## Control flow

```text
MISSION
  -> RVIA ROUTER
  -> SHADOW GLASS policy / identity gate
  -> ONTOLOGY context
  -> GPT-DOUG / VIRGINIA / WAKEUP3LM planning
  -> ZYRA approval / security
  -> XUNIA / NXYZ / ZYRA CLOUD execution
  -> GLASS ONION evidence
  -> BLACK HOUSE mission record
```

## Canonical files

- `ecosystem.yaml` — root system manifest.
- `registry/repositories.json` — authoritative repository registry.
- `registry/services.json` — runtime/service registry.
- `registry/agents.json` — agent/model execution registry.
- `missions/mission.schema.json` — universal mission envelope.
- `ontology/ontology.schema.json` — canonical object/link vocabulary.
- `governance/CONTROL-PLANE.md` — execution and authority boundary.

## State language

Use only these lifecycle states when reporting system status:

`planned`, `implemented`, `ci_verified`, `deployed`, `platform_access`, `authorized_action`, `third_party_approved`.

Implementation never implies deployment, credentials never imply authorization, and external-platform adapters never imply tenant entitlement.
