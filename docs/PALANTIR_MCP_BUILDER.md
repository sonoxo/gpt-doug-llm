# GPT-DOUG -> Zyra Foundry MCP Builder

Target enrollment:

```text
https://zyra.usw-17.palantirfoundry.com
```

Use the enrollment origin above for APIs and MCP. Do **not** configure the browser UI path `/workspace/now/platform` as the API base URL.

This integration uses supported Palantir tool surfaces only. It does not create a bypass channel, hidden credential path, or access outside the permissions granted in Foundry.

## Tool architecture

### 1. Palantir MCP - builder plane

Use Palantir MCP when an external coding agent needs development tools for Foundry itself, including repository context, datasets, transforms, Ontology schema, object types, link types, action types, and other supported development resources.

Authority remains the authenticated Foundry user's/scoped token's permissions and the Control Panel enablement for Palantir MCP.

Local profile:

```bash
python palantir_mcp_profile.py status
python palantir_mcp_profile.py config
```

The secret-free example configuration is:

```text
config/palantir-mcp.zyra.example.json
```

It runs:

```bash
npx -y palantir-mcp --foundry-api-url https://zyra.usw-17.palantirfoundry.com
```

with `FOUNDRY_TOKEN` supplied by the user's environment or secure MCP-client credential store.

### 2. Ontology MCP - runtime/AIP plane

Use Ontology MCP when an external agent needs application-scoped runtime tools. Developer Console can expose selected:

- Ontology object types for governed reads;
- action types for governed writes;
- query functions;
- published AIP Logic functions;
- AIP agents/chatbots saved as functions.

Ontology MCP uses the OAuth configuration and restrictions of the Developer Console application. Use authorization-code OAuth for interactive user-scoped agents, or client-credentials OAuth for a service-to-service agent.

Set the connection URL supplied by Developer Console only in local/secret configuration:

```bash
FOUNDRY_ONTOLOGY_MCP_URL=<copy-from-Developer-Console-MCP-page>
```

Do not invent or guess this URL in code.

### 3. Existing REST/AIP fallback

The repo already has a host-pinned REST bridge:

- `palantir_foundry.py` - OAuth/bearer transport, Ontology reads, searches, actions;
- `palantir_aip.py` - AIP LLM proxy and published AIP Logic/Function query execution;
- `palantir_terminal.py` - `/palantir` command surface.

Published Logic/function queries can be invoked with:

```text
/palantir query-types <ontology>
/palantir aip-logic <ontology> <query_api_name> <parameters_json>
```

Ontology actions remain confirmation-gated and require Foundry write permissions.

## Foundry-side enablement

### A. Enable Palantir MCP for builders

A Foundry platform administrator must:

1. Open **Control Panel**.
2. Navigate to **Code Repositories -> Palantir MCP**.
3. Enable Palantir MCP for the user/group that will run the builder agent.
4. Ensure the authenticated user/token has only the project and platform permissions required for the intended build work.
5. Generate/use a Foundry user token only in the local MCP client's secure environment.

Then configure the MCP client with `config/palantir-mcp.zyra.example.json` or equivalent client-specific settings.

### B. Enable Ontology MCP for GPT-DOUG/AIP runtime tools

In **Developer Console**:

1. Open or create the application that represents GPT-DOUG/Zyra.
2. Add only the Ontology resources the agent should be allowed to use.
3. Configure OAuth and application restrictions.
4. Open the **MCP** page in the application.
5. Enable the MCP server.
6. Copy the exact MCP connection details supplied by Foundry.
7. Verify the tools listed by the MCP client match the application's configured object types, actions, and query functions.
8. Give actions precise **Agent tool descriptions** in Ontology Manager so the model knows when they are appropriate.

For production, prefer tightly restricted action types over generic write capabilities.

## Minimal environment profile

Keep this in local `.env` or a secret manager, never Git:

```bash
FOUNDRY_BASE_URL=https://zyra.usw-17.palantirfoundry.com
FOUNDRY_ALLOWED_HOST=zyra.usw-17.palantirfoundry.com
FOUNDRY_SCOPES="api:ontologies-read api:ontologies-write"
FOUNDRY_ENABLE_WRITES=false

# Choose one REST authentication method:
# FOUNDRY_TOKEN=<secret>
# or:
# FOUNDRY_CLIENT_ID=<secret-id>
# FOUNDRY_CLIENT_SECRET=<secret>

# Supplied by the Developer Console MCP page when Ontology MCP is enabled:
# FOUNDRY_ONTOLOGY_MCP_URL=<mcp-url>
```

Start with `FOUNDRY_ENABLE_WRITES=false`. Turn the REST write gate on only for a workflow that needs Ontology Actions and only after the service user/application has the correct resource permissions.

## Verification sequence

Run these in order:

```bash
python palantir_mcp_profile.py status
python palantir_bridge.py status
python palantir_bridge.py ontologies
```

Then inside GPT-DOUG:

```text
/palantir status
/palantir ontologies
/palantir query-types <ontology>
```

Finally verify the external MCP client can list Palantir MCP builder tools and the Developer Console Ontology MCP tools expected for the application.

## What this enables

Once the Foundry administrator enables Palantir MCP and the Developer Console application exposes Ontology MCP, an authorized MCP-capable agent can:

- inspect Foundry repositories and development context;
- build or update supported Ontology schema resources on branches;
- work with datasets/transforms through the supported Palantir MCP toolset;
- query permitted Ontology data;
- invoke published AIP Logic/functions;
- call only the action types explicitly exposed by the Developer Console application.

The actual tool list is determined by Palantir version, tenant enablement, application restrictions, and user/service permissions. No local flag manufactures access.
