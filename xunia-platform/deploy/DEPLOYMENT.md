# XUNIA Platform deployment runbook

## Production gates

1. Build and test the exact commit that will be deployed.
2. Set `XUNIA_AUTH_REQUIRED=1` and provide at least one admin API key usable in the deployment realm.
3. Mount a persistent writable directory at `XUNIA_DATA_DIR`.
4. Put TLS in front of port 4400 with your ingress/reverse proxy. Do not expose plaintext HTTP over an untrusted network.
5. Restrict `XUNIA_CORS_ORIGIN` to the exact browser origin if cross-origin access is required.
6. Keep `XUNIA_METRICS_PUBLIC=0` unless the metrics network is already isolated.
7. Configure model tokens, API keys, state-encryption keys, and other secrets only through a secret manager or runtime secret mechanism.
8. Back up the data directory and the state-encryption key separately. The data directory contains ontology state, AIP runs, and the hash-chained audit trail.
9. In sovereign mode, pin `XUNIA_REALM_ID`, `XUNIA_REGION`, and `XUNIA_ALLOWED_REGIONS`, and review every external origin in `XUNIA_EGRESS_ALLOWLIST`.

## Generate API keys

Example:

```bash
ADMIN_TOKEN=$(openssl rand -hex 32)
OPERATOR_TOKEN=$(openssl rand -hex 32)
printf '%s\n' "$ADMIN_TOKEN" "$OPERATOR_TOKEN"
```

Then set realm-bound credentials when sovereignty is enforced:

```bash
export XUNIA_API_KEYS="{\"$ADMIN_TOKEN\":{\"role\":\"admin\",\"subject\":\"platform-admin\",\"realm\":\"xunia-us-va\"},\"$OPERATOR_TOKEN\":{\"role\":\"operator\",\"subject\":\"platform-operator\",\"realm\":\"xunia-us-va\"}}"
```

Never commit the generated values.

## State-encryption key

Sovereign encrypted persistence uses an AES-256-GCM key supplied as base64 encoding of exactly 32 random bytes:

```bash
STATE_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')
printf '%s\n' "$STATE_ENCRYPTION_KEY"
```

Store this key in your KMS/secret manager and back it up separately from the encrypted data. Losing it makes encrypted state unrecoverable. Do not rotate it by simply replacing the environment variable on an existing data directory; decrypt/re-encrypt state through an approved migration procedure.

`XUNIA_CUSTOMER_KEY_ID` is an operator-defined identifier for the customer-controlled KMS/HSM boundary, for example `kms://customer/xunia/us-va/platform-state`. It is metadata used by sovereignty readiness and does not replace `XUNIA_STATE_ENCRYPTION_KEY`.

## Docker Compose

```bash
cp .env.example .env
# Replace placeholder keys, sovereignty values, state-encryption key, and integration URLs in .env
docker compose up --build -d
curl -fsS http://127.0.0.1:4400/health
curl -fsS http://127.0.0.1:4400/ready
```

Open the console on port 4400 and enter an API key in the top bar. The browser stores it only in `sessionStorage` for that tab/session.

## Kubernetes

Build and publish the container, replace `ghcr.io/REPLACE_ORG/xunia-platform:1.0.0` in `deploy/k8s.yaml`, then create all three Secret fields required by the checked-in Deployment:

```bash
ADMIN_TOKEN=$(openssl rand -hex 32)
STATE_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')
CUSTOMER_KEY_ID='kms://customer/xunia/us-va/platform-state'

kubectl create secret generic xunia-platform-secrets \
  --from-literal=api-keys="{\"$ADMIN_TOKEN\":{\"role\":\"admin\",\"subject\":\"platform-admin\",\"realm\":\"xunia-us-va\"}}" \
  --from-literal=customer-key-id="$CUSTOMER_KEY_ID" \
  --from-literal=state-encryption-key="$STATE_ENCRYPTION_KEY"

kubectl apply -f deploy/k8s.yaml
kubectl rollout status deployment/xunia-platform
```

The manifest references these exact Secret keys:

```text
api-keys
customer-key-id
state-encryption-key
```

Terminate TLS at the cluster ingress or service mesh. The included NetworkPolicy defaults outbound traffic to deny and explicitly permits the internal XUNIA Chain and SONOXO service paths defined by the manifest; add any approved DNS or external model-gateway egress deliberately and keep application-level `XUNIA_EGRESS_ALLOWLIST` consistent with the network policy.

## Operations

- Liveness: `GET /health`
- Readiness: `GET /ready`
- Prometheus text metrics: `GET /metrics` (viewer auth by default)
- Audit integrity: `GET /api/aip/audit/verify`
- Runtime status: `GET /api/platform/status`

A graceful `SIGTERM` drains the HTTP server for up to 10 seconds. Persistent state is written atomically before mutating API calls return.

## Backup / restore

Stop writes or stop the service, then back up the complete `XUNIA_DATA_DIR`. Back up the state-encryption key separately in the approved key-management system. Restore by mounting the saved directory at the same path and supplying the same encryption key before startup. The readiness endpoint reports persistence/key errors, and the audit verification endpoint validates the hash chain after restore.
