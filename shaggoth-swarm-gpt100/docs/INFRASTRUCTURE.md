# Shaggoth Infrastructure

The infrastructure layer supports two deployment targets:

- Docker Compose for a single authorized host.
- Kubernetes for a horizontally scaled cluster.

## Docker Compose

From `shaggoth-swarm-gpt100`:

```bash
cp infra/compose/.env.example infra/compose/.env
docker compose --env-file infra/compose/.env -f infra/compose/compose.yml up -d --build
curl http://127.0.0.1:8787/health
```

The API binds to loopback by default. Change `SHAGGOTH_BIND_ADDRESS` only when the surrounding network and firewall are intentionally configured for remote access.

The persistent connector is an optional Compose profile and still requires explicit authorized endpoints:

```bash
docker compose --env-file infra/compose/.env -f infra/compose/compose.yml --profile connectors up -d --build
```

## Kubernetes

Build and push `shaggoth-swarm-gpt100:0.3.0` to an approved registry, then update the image reference in `infra/k8s/deployment.yaml`.

Render the base:

```bash
kubectl kustomize infra/k8s
```

Apply it:

```bash
kubectl apply -k infra/k8s
```

The base creates:

- two API replicas
- ClusterIP service
- horizontal pod autoscaler, 2-10 replicas
- pod disruption budget
- non-token-bearing service account
- non-root/read-only containers
- default-deny ingress and egress
- DNS-only egress
- namespace-local API ingress

External network access is intentionally not open in the base. If the swarm must reach an approved model/API endpoint, add an egress policy for the exact authorized ranges or use an approved CNI FQDN policy. The supplied egress example is not included in `kustomization.yaml`.

Secrets are not committed. Copy `secret-example.yaml`, populate it through your cluster's secret-management process, and apply it separately.

The connector deployment example ships at `replicas: 0` and is not included in the base. Enable it only after configuring authorized endpoints and matching egress policy.

The ingress example is also not part of the base. If you expose the API through an ingress controller, pair it with authentication, TLS, and an ingress NetworkPolicy appropriate to that controller namespace.

## Security defaults

- non-root UID/GID 65532
- read-only root filesystem
- Linux capabilities dropped
- no privilege escalation
- seccomp RuntimeDefault on Kubernetes
- no Kubernetes API token mounted
- ClusterIP service by default
- default-deny ingress/egress in Kubernetes
- API bound to loopback by default in Compose
- no host networking or privileged containers
- no hidden persistence
