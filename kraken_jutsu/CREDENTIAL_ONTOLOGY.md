# Kraken Credential Ontology -- local governance API

This is a **local, standard-library, metadata-only** inventory for credentials
that an authorized operator chooses to register. It does not find raw keys,
scan repositories, access keychains, mint provider tokens, prevent account
revocation, bypass patches, or extend permissions. Provider approval and the
user's continuing authorization are prerequisites for credential renewal.

## Quick start (from repository root)

```sh
bash scripts/doug-max credential-ontology init
bash scripts/doug-max credential-ontology serve
```

The API listens exclusively on `127.0.0.1:8765`. Run `schema` to inspect the
ontology without touching the local ledger:

```sh
bash scripts/doug-max credential-ontology schema
```

The `init` command creates `~/.gpt-doug/kraken-credential-ontology/` and an
owner-only `operator.token` file plus a local SQLite ledger, with no raw
credential values. It **never displays** the operator token. The operator
can use it locally to send authenticated requests:

```sh
TOKEN=$(cat "$HOME/.gpt-doug/kraken-credential-ontology/operator.token")
curl -fsS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/v1/ontology
```

For metadata about a credential the operator already administers:

```sh
curl -fsS -X POST http://127.0.0.1:8765/v1/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"provider":"aws","alias":"amp-writer","kind":"iam-role","owner_role":"operator","rotation_days":90,"expires_on":null}'
```

This returns a locally generated *record identifier*, **not an AWS key**. To
request approved rotation, POST `{"credential_id":"<record_uuid>",
"reason":"scheduled"}` to `/v1/rotation-requests`. A request is left in
`PENDING_PROVIDER_APPROVAL`; no external provider call or key issuance takes
place. Query `/v1/rotation-requests` to review outstanding records.

To **record** a revocation performed at the provider, POST
`{"credential_id":"<record_uuid>"}` to `/v1/record-revocation`.
It marks the local record revoked and cancels pending rotations. The API does
**not** execute provider-side revocation or verify the provider's state.

## Access/API surface

| Method | Endpoint | Outcome |
|---|---|---|
| GET | `/v1/ontology` | Public schema, delivered only after local operator authentication |
| GET | `/v1/credentials` | Registered metadata, never secret values |
| POST | `/v1/credentials` | Validate/register metadata; deny unknown/secret fields |
| GET | `/v1/rotation-requests` | Inspect provider-approval requests |
| POST | `/v1/rotation-requests` | Create one pending request per credential |
| POST | `/v1/record-revocation` | Record local revoked status and cancel pending requests |
| GET | `/v1/audit` | Last 100 local metadata actions |

All endpoints require a random bearer token loaded from an owner-only local file.
The HTTP server rejects non-loopback binding and emits no CORS headers.
Use only for local development; it is **not a remotely exposed identity
provider**. Its audit trail is an operational history, not tamper-proof.

For AWS, prefer IAM roles and temporary STS credentials rather than long-term
keys. For GitHub, use installed GitHub Apps with provider-mediated, expiring
tokens. Both are contingent on provider authorization and can be revoked.

## Verify

```sh
python3 -m unittest tests.test_kraken_credential_ontology -v
```

No paid services, external calls, API key secrets, or model tokens are needed.
