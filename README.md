# GPT-Doug QBio // Repo One seed project

**Classification:** UNCLASSIFIED - NO CUI

This directory is a **standalone project seed** for Repo One / Platform One. It is
intentionally separated from the GPT-Doug monorepo because current Party Bus
onboarding guidance prohibits monolithic repositories for deployment pipelines.

## Scope

The service exposes only:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/capabilities`
- `POST /v1/analyze`

The analysis endpoint accepts ordered spike-count frames and returns the existing
GPT-Doug QBio descriptive analytics. It has **no stimulation, hardware-control,
autonomous-actuation, outbound-network, or persistent-storage path**.

Simulator output remains explicitly distinct from measured read-only data.

## Local validation

~~~sh
python3 -m unittest discover -s tests -v
python3 -m py_compile src/core.py src/service.py
~~~

## Container build

The Dockerfile is shaped for the Iron Bank / Repo One hardening workflow and uses
the Iron Bank UBI 9 minimal base image arguments.

~~~sh
docker build -t gpt-doug-qbio:0.1.0 .
docker run --rm -p 8080:8080 gpt-doug-qbio:0.1.0
~~~

Then:

~~~sh
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8080/v1/capabilities
~~~

Example analysis:

~~~sh
curl -fsS -X POST http://127.0.0.1:8080/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "source_class": "SIMULATED",
    "window": 3,
    "frames": [
      {"t_ms": 0, "counts": [0,0,0,0]},
      {"t_ms": 20, "counts": [1,0,1,0]},
      {"t_ms": 40, "counts": [1,1,1,0]}
    ]
  }'
~~~

## Repo One / Iron Bank submission checklist

Before submitting this project, replace the placeholder maintainer in
`hardening_manifest.yaml` with the actual Repo One account information.

This seed intentionally contains **no `.gitlab-ci.yml`**. Party Bus documentation
states that Mission DevOps creates the deployment pipeline and that product-team
GitLab CI files are not used for that flow.

The standalone Repo One project root must contain:

- `Dockerfile`
- `hardening_manifest.yaml`
- `LICENSE`
- `README.md`
- `renovate.json`
- `src/`
- `tests/`

## Platform One deployment assumptions

Authentication, DNS, ingress, Keycloak roles, staging/production manifests, and any
RDS/S3 resources are deployment-environment concerns and should be configured through
the Platform One onboarding/Mission DevOps process. This service itself requires no
database or S3 bucket.

The container runs as UID 1001, includes a Docker health check, and does not use
Dockerfile `ADD` instructions.
