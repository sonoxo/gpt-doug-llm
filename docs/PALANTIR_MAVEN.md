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

## CONSEC + Gotham Mode

`maven_gotham_mode.py` adds a bounded consequence-analysis layer for defensive decision support:

```text
MAVEN DECISION PACKETS
  -> CONSEC CONSEQUENCE ENVELOPES
  -> GOTHAM SIMULATION VIEW
  -> ARTILLERY ANALYTIC SALVO
  -> HUMAN REVIEW
```

- **CONSEC** scores defensive operational impact across service continuity, data integrity, public safety, recovery complexity, and resource strain.
- **Gotham Mode** is a simulation/visualization profile for organizing fused evidence and consequence envelopes.
- **ARTILLERY** is a metaphor for a batched analytic salvo: up to 25 review items ordered by consequence score and confidence.

This mode intentionally does **not** implement weapon target selection, person-level target ranking, fire control, ballistic calculation, firing solutions, strike recommendations, weapon control, or kinetic execution. Precise coordinates are not emitted in analytic rounds.

Quick local demo:

```bash
python3 maven_gotham_mode.py
pytest -q tests/test_maven_gotham_mode.py
```

The equivalent XUNIA public operator surface is `https://xunia.org/rvia/maven`, with the API supporting `mode: "GOTHAM_SIMULATION"`.

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
