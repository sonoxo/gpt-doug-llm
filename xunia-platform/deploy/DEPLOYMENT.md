# XUNIA Platform deployment runbook

## Production gates

1. Build and test the exact commit that will be deployed.
2. Set `XUNIA_AUTH_REQUIRED=1` and provide at least one admin API key.
3. Mount a persistent writable directory at `XUNIA_DATA_DIR`.
4. Put TLS in front of port 4400 with your ingress/reverse proxy. Do not expose plaintext HTTP over an untrusted network.
5. Restrict `XUNIA_CORS_ORIGIN` to the exact browser origin if cross-origin access is required.
6. Keep `XUNIA_METRICS_PUBLIC=0` unless the metrics network is already isolated.
7. Configure `XUNIA_MODEL_TOKEN`, API keys, and other secrets only through a secret manager or runtime secret mechanism.
8. Back up the data directory. It contains ontology state, AIP runs, and the hash-chained audit trail.

## Generate API keys

Example:

```bash
ADMIN_TOKEN=$(openssl rand -hex 32)
OPERATOR_TOKEN=$(openssl rand -hex 32)
printf '%s\n' "$ADMIN_TOKEN" "$OPERATOR_TOKEN"
```

Then set:

```bash
export XUNIA_API_KEYS="{\"$ADMIN_TOKEN\":{\"role\":\"admin\",\"subject\":\"platform-admin\"},\"$OPERATOR_TOKEN\":{\"role\":\"operator\",\"subject\":\"platform-operator\"}}"
```

Never commit the generated values.

## Docker Compose

```bash
cp .env.example .env
# Replace placeholder keys and integration URLs in .env
docker compose up --build -d
curl -fsS http://127.0.0.1:4400/health
curl -fsS http://127.0.0.1:4400/ready
```

Open the console on port 4400 and enter an API key in the top bar. The browser stores it only in `sessionStorage` for that tab/session.

## Kubernetes

Build and publish the container, replace `ghcr.io/REPLACE_ORG/xunia-platform:1.0.0` in `deploy/k8s.yaml`, then create the secret and apply the manifest:

```bash
kubectl create secret generic xunia-platform-secrets \
  --from-literal=api-keys='{"REPLACE_LONG_RANDOM_TOKEN":{"role":"admin","subject":"platform-admin"}}'
kubectl apply -f deploy/k8s.yaml
kubectl rollout status deployment/xunia-platform
```

Terminate TLS at the cluster ingress or service mesh and apply your organization’s network policies around the service.

## Operations

- Liveness: `GET /health`
- Readiness: `GET /ready`
- Prometheus text metrics: `GET /metrics` (viewer auth by default)
- Audit integrity: `GET /api/aip/audit/verify`
- Runtime status: `GET /api/platform/status`

A graceful `SIGTERM` drains the HTTP server for up to 10 seconds. Persistent state is written atomically before mutating API calls return.

## Backup / restore

Stop writes or stop the service, then back up the complete `XUNIA_DATA_DIR`. Restore by mounting the saved directory at the same path before startup. The readiness endpoint reports persistence errors, and the audit verification endpoint validates the hash chain after restore.
