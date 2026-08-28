# GPT-DOUG-LLM → Palantir Foundry

This repo now has a direct Foundry connection for an authorized Palantir enrollment.

## What is connected

GPT-DOUG can:

- authenticate to Foundry with OAuth client credentials or an issued bearer token;
- list available Ontologies;
- list object types;
- read and search Ontology objects;
- load Foundry objects into a GPT-DOUG prompt as grounding context;
- apply an Ontology Action only when Foundry writes are explicitly enabled and the terminal user confirms the action.

The connection is limited to the Foundry host and permissions assigned to the configured Palantir application/service user.

## Configure

Copy `.env.example` to `.env` and set the values supplied by your Palantir Developer Console application:

```bash
FOUNDRY_BASE_URL=https://your-foundry-host
FOUNDRY_ALLOWED_HOST=your-foundry-host
FOUNDRY_CLIENT_ID=your-client-id
FOUNDRY_CLIENT_SECRET=your-client-secret
FOUNDRY_SCOPES=api:ontologies-read
FOUNDRY_ENABLE_WRITES=false
```

You can use `FOUNDRY_TOKEN` instead of client ID/client secret when you have an explicitly issued bearer token.

Do not commit credentials.

## Use from GPT-DOUG

Start GPT-DOUG normally and use:

```text
/palantir
/palantir ontologies
/palantir object-types <ontology>
/palantir objects <ontology> <object_type> [limit]
/palantir get <ontology> <object_type> <primary_key>
/palantir search <ontology> <object_type> <json_body>
/palantir ask <ontology> <object_type> <question>
```

`/palantir ask` retrieves authorized Foundry objects and sends that data through the normal GPT-DOUG compliance, Zyra, Golden Shield, and model path as grounding context.

## Foundry Actions

Actions are locked twice:

1. Set scopes that include `api:ontologies-write` and set `FOUNDRY_ENABLE_WRITES=true`.
2. Confirm the action in the GPT-DOUG terminal.

Then use:

```text
/palantir action <ontology> <action_api_name> {"parameter":"value"}
```

The Palantir application/service user must still have permission to the target Ontology resources and Action type. The local switch does not grant Palantir permissions.

## Direct command-line bridge

The same connection can be checked without launching the full terminal:

```bash
python palantir_bridge.py status
python palantir_bridge.py ontologies
python palantir_bridge.py object-types <ontology>
python palantir_bridge.py objects <ontology> <object_type>
python palantir_bridge.py analyze <ontology> <object_type> "your question"
```

This code does not contain or manufacture Palantir credentials. It uses the credentials and access that are actually assigned to the configured Foundry application.
