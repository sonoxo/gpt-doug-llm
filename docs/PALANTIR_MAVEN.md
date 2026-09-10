# Palantir Maven — GPT-DOUG / GPT-REDPANDA

This repository supports an **authorized Palantir Foundry Artifact Repository** configured for Maven. The code does not create Palantir entitlements, repositories, or credentials by itself.

## Foundry-side prerequisite

Inside your authorized Foundry enrollment:

1. Create or open a Project.
2. Create an **Artifact Repository**.
3. Open **Publish** and select **Maven**.
4. Generate the publishing credentials/instructions.
5. Copy the generated Maven repository URL and credentials into your local environment only.

Never commit a generated token.

## Local wiring

```bash
export PALANTIR_MAVEN_REPOSITORY_URL='https://<generated-repository-url>'
export PALANTIR_MAVEN_REPOSITORY_ID='palantir-foundry'
export PALANTIR_MAVEN_USERNAME='<generated-username-if-required>'
export PALANTIR_MAVEN_TOKEN='<generated-token>'
export PALANTIR_MAVEN_ALLOWED_HOST='<exact-host-from-repository-url>'
```

Then run:

```bash
python3 palantir_maven.py status
python3 palantir_maven.py probe
```

GPT-REDPANDA exposes the same checks:

```bash
bash redpanda-desktop/palantir-maven status
bash redpanda-desktop/palantir-maven probe
bash redpanda-desktop/palantir-maven kraken
```

`kraken` is a local verification command. It validates the ontology JSON, Python adapter syntax, and Maven environment configuration. It does **not** publish artifacts or call a Foundry Action.

## Maven settings

To generate a temporary Maven settings file without committing credentials:

```bash
python3 palantir_maven.py settings > /tmp/palantir-settings.xml
chmod 600 /tmp/palantir-settings.xml
```

Use the generated repository URL and repository id in your Maven/Gradle project exactly as provided by your Foundry Artifact Repository instructions.

## Glass Onion ontology

The integration is registered at:

```text
safety-shield/ontology/palantir-maven-glass-onion.json
```

The graph models:

```text
GPT-DOUG ───────┐
                ├── consumes ──> Palantir Foundry Maven Artifact Repository
GPT-REDPANDA ───┘                        │
         │                               ├── publishes MavenArtifact
         └── CPR verifies ───────────────┘
         │
         └── observed by ──> GLASS ONION
```

Publishing remains explicit and human-authorized. Secrets remain environment-only.
