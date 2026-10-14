# Platform One / Repo One final handoff

There are now two separate deliverables:

1. `platform_one/repo1-qbio/` — upstream application/source seed and local tests.
2. `platform_one/repo1-hardening/` — **Repo One hardening-only project**.

Use the second one for current Iron Bank onboarding.

Current Iron Bank repository guidance says the onboarding team creates the Repo One
project, the integration branch is `development`, contributors work on feature
branches, and the security team performs the merge to `master`.

The hardening-only project therefore contains no application source or binary files.
Instead, its manifest downloads the two required source files from an immutable GitHub
commit and validates each with SHA-256 before the Docker build.

## Export

~~~sh
bash scripts/export-repo1-hardening.sh
~~~

That creates `repo1-qbio-hardening-export/`.

## Before the first Repo One push

Edit the three maintainer placeholders in
`repo1-qbio-hardening-export/hardening_manifest.yaml` with the actual Repo One
GitLab account values assigned to the maintainer.

Then set the Repo One remote supplied by onboarding and push a feature branch:

~~~sh
cd repo1-qbio-hardening-export
git init
git add .
git commit -m "Initial GPT-Doug QBio Iron Bank hardening submission"
git branch -M feature/gpt-doug-qbio-0.1.0
git remote add repo1 https://repo1.dso.mil/<ASSIGNED-GROUP>/<ASSIGNED-PROJECT>.git
git push -u repo1 feature/gpt-doug-qbio-0.1.0
~~~

Do not push directly to `master`. If the onboarding-created project already has a
required starter commit or `.gitlab/` content, clone that project first and copy
these hardening files into a feature branch rather than overwriting its history.
