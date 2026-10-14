# GPT-Doug // Platform One / Repo One readiness

This repository is a large multi-component monorepo. Current Platform One Party Bus
guidance says monolithic repositories are prohibited for deployment pipelines and a
valid Dockerfile must exist at the root of each deployable project.

For that reason, the first Platform One-ready unit is maintained under:

`platform_one/repo1-qbio/`

It is designed to be exported as its **own Repo One GitLab project**, where its
`Dockerfile`, `hardening_manifest.yaml`, `LICENSE`, and `README.md` become the
project root.

## Why QBio first

The QBio service is a bounded, stateless, read-only workload. It does not require RDS,
S3, privileged containers, hardware access, stimulation, or autonomous actuation.
That keeps the initial Repo One / Iron Bank surface small enough to harden and review.

## Required external onboarding actions

Software preparation alone does not create a Repo One project or Platform One pipeline.

1. Register/sign in to Repo One through Platform One SSO.
2. Complete the appropriate Platform One / Iron Bank onboarding request.
3. Use the GitLab project created/approved by the onboarding team.
4. Replace the placeholder maintainer fields in `hardening_manifest.yaml`.
5. Push/import the standalone seed into that project.
6. Let the Platform One / Container Hardening workflow create and scan the pipeline.
7. Address SAST/container/STIG/CVE findings through the assigned Repo One issue.

Do not add a product-owned `.gitlab-ci.yml` for the Party Bus path; current Mission
DevOps guidance says those files are not allowed in that deployment flow.

## Planned decomposition

Do not move the entire GPT-Doug monorepo into one Party Bus project. Split only
deployable, bounded services:

- `gpt-doug-qbio`: read-only spike analytics;
- ontology API: provenance/evidence query service;
- observability UI: stateless presentation tier;
- optional data adapter(s): separately authorized source-specific integrations.

Each deployable service should have its own Repo One project and root Dockerfile.
