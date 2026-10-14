# GPT-Doug QBio — Iron Bank / Repo One hardening project

**Classification: UNCLASSIFIED — NO CUI**

This is the hardening-only Repo One project for GPT-Doug QBio. It deliberately
contains **no application source code or binaries**. The two Python application
files are immutable external resources pinned to a GitHub commit and verified by
lowercase SHA-256 checksums in `hardening_manifest.yaml`.

## Image behavior

The resulting container exposes a single read-only HTTP service on port 8080.

Endpoints:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/capabilities`
- `POST /v1/analyze`

The service has no stimulation endpoint, hardware actuation, outbound-network
client in the request path, database, persistent data store, secret store, or
autonomous execution surface.

## Iron Bank build inputs

The pipeline obtains:

- `core.py`
- `service.py`

from the immutable GitHub commit identified in `hardening_manifest.yaml`. The
pipeline must validate each resource checksum before the Docker build begins.

The Dockerfile uses the hardened Iron Bank UBI9-minimal base, runs as numeric
UID 1001, contains no `ADD` instruction, performs no Internet download, and
contains no OCI `LABEL` directives. Image metadata lives in the manifest.

## Required maintainer edit before submission

Replace exactly these three values in `hardening_manifest.yaml`:

- `REPLACE_WITH_REPO1_EMAIL`
- `REPLACE_WITH_MAINTAINER_NAME`
- `REPLACE_WITH_REPO1_USERNAME`

Do not substitute a GitHub username unless it is also your actual Repo One
GitLab username.

## Repo One workflow

The onboarding team creates the project. Current Iron Bank guidance uses
`development` as the integration branch and requires contributor work on a
feature branch. The Container Hardening Team performs the merge to `master`
after verification.

Do not create a product-owned pipeline file unless the assigned Repo One
onboarding process explicitly requires one.

## Source provenance

Source repository:
`https://github.com/sonoxo/gpt-doug-llm`

Pinned source commit:
`ae81a7dcceac5d27b5d42d9614a71d296abc6f18`

The application source remains in the upstream source repository; this Repo One
project is only the container hardening definition.
