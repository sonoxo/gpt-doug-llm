# GPT-Doug QBio — Iron Bank / Repo One hardening project

**Classification: UNCLASSIFIED — NO CUI**

This is the hardening project for GPT-Doug QBio. The repository contains the
container definition and the permitted runtime entrypoint under `scripts/`. The
QBio analysis library itself is fetched as an immutable external resource pinned
to a GitHub commit and verified by lowercase SHA-256 in
`hardening_manifest.yaml`.

## Container purpose

The resulting image exposes one read-only HTTP analytics service on port 8080.

Endpoints:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/capabilities`
- `POST /v1/analyze`

The service has no stimulation endpoint, hardware actuation, autonomous
execution path, database, persistent data store, or application secret store.

## Iron Bank build inputs

The pipeline obtains `core.py` from the immutable GitHub commit identified in
`hardening_manifest.yaml` and validates its SHA-256 checksum before the Docker
build. The runtime entrypoint `scripts/service.py` is stored directly in the
Repo One project as required for scripts used by the container.

The Dockerfile uses the hardened Iron Bank UBI9-minimal base, runs as numeric
UID 1001, contains no `ADD` instruction, performs no Internet download, and
contains no OCI `LABEL` directives. Image metadata lives in the manifest.

## Kubernetes deployment

Iron Bank containers are intended for Kubernetes production deployment. A
minimal deployment is:

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpt-doug-qbio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gpt-doug-qbio
  template:
    metadata:
      labels:
        app: gpt-doug-qbio
    spec:
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpt-doug-qbio
          image: registry1.dso.mil/ironbank/opensource/sonoxo/gpt-doug-qbio:0.1.0
          ports:
            - name: http
              containerPort: 8080
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
              ephemeral-storage: "64Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
              ephemeral-storage: "256Mi"
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            initialDelaySeconds: 2
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: gpt-doug-qbio
spec:
  selector:
    app: gpt-doug-qbio
  ports:
    - name: http
      port: 8080
      targetPort: http
  type: ClusterIP
~~~

Use an approved ingress/service-mesh layer for authentication, authorization,
TLS, rate limiting, and external exposure.

## Recommended resource envelope

These values are conservative starting points for this stateless Python service
and should be tuned from workload measurements in the target environment.

| Resource | Minimum | Desired | Maximum |
| --- | ---: | ---: | ---: |
| CPU | 50m | 100m | 500m |
| Memory | 64Mi | 128Mi | 256Mi |
| Ephemeral storage | 16Mi | 64Mi | 256Mi |
| Persistent volumes | 0 | 0 | 0 |
| Containers / replicas | 1 | 1–2 | 10 |

The application does not require persistent storage or mounted data volumes.

## Required maintainer edit before submission

Replace exactly these three values in `hardening_manifest.yaml`:

- `REPLACE_WITH_REPO1_EMAIL`
- `REPLACE_WITH_MAINTAINER_NAME`
- `REPLACE_WITH_REPO1_USERNAME`

Do not substitute a GitHub username unless it is also the actual Repo One
GitLab username.

## Repo One workflow

The onboarding team creates the project. Current Iron Bank guidance uses
`development` as the integration branch and requires contributor work on a
feature branch. The Container Hardening Team performs the merge to `master`
after verification.

Do not overwrite onboarding-created `.gitlab/` content and do not create a
product-owned pipeline definition unless the assigned Repo One workflow
explicitly requires one.

## Source provenance

Upstream source repository:
`https://github.com/sonoxo/gpt-doug-llm`

Pinned application source commit:
`ae81a7dcceac5d27b5d42d9614a71d296abc6f18`

The QBio library comes from that immutable source commit. The Repo One
`scripts/service.py` entrypoint is copied from the same source revision.
