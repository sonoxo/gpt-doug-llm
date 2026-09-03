# GPT-DOUG-LLM → Palantir Platform

This repo contains a bounded integration architecture for an **authorized Palantir enrollment**. It does not manufacture Palantir licensing, credentials, entitlements, government affiliation, or access.

## Integrated platform model

```text
                    GPT-DOUG / VIRGINIA-LLM / RVIA
                                  │
                                  ▼
                              PALANTIR AIP
                     agents · logic · evals · automation
                                  │
                                  ▼
                         PALANTIR ONTOLOGY
                objects · links · properties · actions
                         │                    │
                         ▼                    ▼
                     GOTHAM               JUPYTERLAB
              mission/intel view       Code Workspaces
                         │                    │
                         └──────────┬─────────┘
                                    ▼
                                  APOLLO
                      governed release + deployment
```

Palantir's current public architecture describes AIP + Foundry + Apollo as an integrated enterprise operating system. The Ontology is the operational object/action layer used by both humans and AI. Gotham can consume supported Foundry Ontology types when the enrollment is configured for Gotham integration. JupyterLab is available through Foundry Code Workspaces and can interact with Ontology resources.

## What is implemented in this repo

### Ontology / Foundry REST bridge

GPT-DOUG can:

- authenticate to Foundry with OAuth client credentials or an issued bearer token;
- list available Ontologies;
- list object types;
- read and search Ontology objects;
- load Foundry objects into a GPT-DOUG prompt as grounding context;
- apply an Ontology Action only when Foundry writes are explicitly enabled and the terminal user confirms the action.

The connection is limited to the Foundry host and permissions assigned to the configured Palantir application/service user.

### Palantir stack registry

`palantir_stack.py` maps the five requested platform planes into Virginia-LLM routing semantics:

| Plane | Virginia-LLM role | Local integration |
| --- | --- | --- |
| **AIP** | agent reasoning, LLM workflows, automations, evals | explicit capability flag + Foundry enrollment |
| **Ontology** | governed operational objects/state/actions | live Foundry REST bridge |
| **Gotham** | authorized mission/intelligence operational view | enrollment-side Gotham integration / type mapping |
| **Apollo** | software delivery and deployment orchestration | operator-managed deployment plane |
| **JupyterLab** | notebooks, model development, analysis, Ontology interaction | Foundry Code Workspaces |

The requested label **`jupiter` is normalized to `JupyterLab`** because that is the IDE/workspace capability documented by Palantir. No Palantir product named Jupiter was verified for this integration.

## Configure

Copy `.env.example` to `.env` and set values supplied by your authorized Palantir environment:

```bash
FOUNDRY_BASE_URL=https://your-foundry-host
FOUNDRY_ALLOWED_HOST=your-foundry-host
FOUNDRY_CLIENT_ID=your-client-id
FOUNDRY_CLIENT_SECRET=your-client-secret
FOUNDRY_SCOPES=api:ontologies-read
FOUNDRY_ENABLE_WRITES=false

PALANTIR_AIP_ENABLED=false
PALANTIR_GOTHAM_ENABLED=false
PALANTIR_APOLLO_ENABLED=false
PALANTIR_JUPYTER_ENABLED=false
```

You can use `FOUNDRY_TOKEN` instead of client ID/client secret when you have an explicitly issued bearer token.

The `PALANTIR_*_ENABLED` flags are **declarative capability gates only**. Setting one to `true` does not create Palantir access; the corresponding Palantir enrollment, entitlement, permissions, markings and deployment configuration must actually exist.

Do not commit credentials.

## Use from GPT-DOUG

Start GPT-DOUG normally and use:

```text
/palantir stack
/palantir status
/palantir ontologies
/palantir object-types <ontology>
/palantir objects <ontology> <object_type> [limit]
/palantir get <ontology> <object_type> <primary_key>
/palantir search <ontology> <object_type> <json_body>
/palantir ask <ontology> <object_type> <question>
```

`/palantir stack` works without credentials and reports which integration planes are configured locally. It never claims that a Palantir enrollment has granted access.

`/palantir ask` retrieves authorized Foundry objects and sends that data through the normal GPT-DOUG compliance, Zyra, Golden Shield, and model path as grounding context.

## Foundry / Ontology Actions

Actions are locked twice:

1. Set scopes that include the required write permission and set `FOUNDRY_ENABLE_WRITES=true`.
2. Confirm the action in the GPT-DOUG terminal.

Then use:

```text
/palantir action <ontology> <action_api_name> {"parameter":"value"}
```

The Palantir application/service user must still have permission to the target Ontology resources and Action type. The local switch does not grant Palantir permissions.

## AIP routing contract

Virginia-LLM uses this routing model:

```text
question / mission
  ↓
AIP-style plan + eval
  ↓
Ontology query
  ↓
policy + identity check
  ↓
optional governed Ontology Action
  ↓
Gotham operational consumption OR Jupyter analysis
  ↓
Apollo-governed release/deployment when applicable
  ↓
audit + validation
```

This is a provider-aligned architectural contract. Actual AIP Logic, Gotham, Apollo or Code Workspace execution requires those capabilities to be provisioned in the operator's Palantir environment.

## Direct command-line bridge

The Foundry/Ontology connection can be checked without launching the full terminal:

```bash
python palantir_bridge.py status
python palantir_bridge.py ontologies
python palantir_bridge.py object-types <ontology>
python palantir_bridge.py objects <ontology> <object_type>
python palantir_bridge.py analyze <ontology> <object_type> "your question"
```

## Canonical machine-readable knowledge

- `safety-shield/agents/knowledge/palantir-stack-v1.json` — platform routing and truthfulness contract.
- `safety-shield/agents/knowledge/rvia-agentic-core.json` — inherited Virginia-LLM / RVIA runtime knowledge contract.
- `palantir_stack.py` — runtime capability registry.
- `palantir_foundry.py` — Foundry/Ontology REST client.
- `palantir_terminal.py` — GPT-DOUG terminal integration.

## Official references

- Palantir architecture center: AIP, Foundry and Apollo
- Palantir AIP overview and architecture
- Palantir Ontology documentation
- Gotham API and Foundry/Gotham integration documentation
- Foundry Code Workspaces / JupyterLab documentation

The repo uses these sources as architectural references and does not claim endorsement or partnership by Palantir Technologies.
