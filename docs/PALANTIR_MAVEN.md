# Palantir Maven — GPT-DOUG / GPT-REDPANDA

This repo supports an **authorized Palantir Foundry Artifact Repository** configured for Maven. It does not create Palantir access, licensing, entitlements, repositories, or credentials.

## Foundry prerequisite

Inside your authorized Foundry Project:

1. Select **New**.
2. Choose **Artifact Repository**.
3. Open the new repository.
4. Open **Publish** and choose **Maven**.
5. Generate the publishing instructions/credentials.
6. Copy the generated repository URL and credentials into your local environment only.

Never commit the generated token.

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
bash redpanda-desktop/palantir-maven kraken
```

`kraken` validates the ontology JSON, Python adapter syntax, and Maven environment configuration. It does **not** publish artifacts or call a Foundry Action.

## Temporary Maven settings

```bash
python3 palantir_maven.py settings > /tmp/palantir-settings.xml
chmod 600 /tmp/palantir-settings.xml
```

Use the repository URL and id exactly as supplied by your Foundry Artifact Repository instructions.

## Glass Onion graph

The integration is registered in:

```text
safety-shield/ontology/palantir-maven-glass-onion.json
```

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
