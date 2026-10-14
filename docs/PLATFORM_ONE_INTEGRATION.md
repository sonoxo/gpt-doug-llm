# GPT-Doug-LLM / GPT-Doug-MLM: Platform One Integration Guide

Status: **documentation-only, no Platform One integration or access implied**.

## Primary sources (official)

- Platform One documentation: https://p1docs.dso.mil/
- Account creation: https://p1docs.dso.mil/p1/get-started/create-a-p1-account
- Platform One resource center: https://p1.dso.mil/resources
- Application access requirements: https://p1docs.staging.dso.mil/p1/get-application-access/request-application-access (staging reference; confirm production guidance)
- User-provided onboarding document URL: https://login.dso.mil/auth/realms/baby-yoda/onboarding/documents (requires user-session authentication; contents not independently verified)

## Current research architecture

- GPT-Doug-LLM: orchestration with ontology-grounded policy and human oversight.
- GPT-Doug-MLM: multidimensional research engine; `biochip_research.py` adds local, explicit model adapters and provenance-labeled observational records.
- Data scope: synthetic observations by default. Live neural data requires documented permission, privacy impact review, owner-approved SDK integration, retention and access policies.
- No defense-network connection, production deployment, or platform certification exists merely by linking documentation.

## Platform One adoption checklist

1. **Account and identity:** Use only your own provisioned Platform One account, required approved credentials/MFA, and organizational identity. Never store P1 passwords, session cookies, CAC material, or bearer tokens in a git repository.
2. **Access authorization:** Request explicitly approved access via your sponsoring organization / onboarding supervisor. A P1 account alone does not convey access to GitLab, Jira, Confluence, Mattermost, IL4/IL5 resources, or protected APIs.
3. **Environment choice:** Have the authorized security owner determine IL2/IL4/IL5 applicability and data handling. Do not upload controlled, classified or regulated data to this public GitHub repository.
4. **Build pipeline:** Validate tests, lint, dependency audit, SBOM, image scanning, provenance and immutable image digests in an isolated test environment. Assess Iron Bank base images and Platform One Party Bus options only under applicable onboarding and licensing agreements.
5. **Deployment:** Use a separately approved service project, dedicated identity, secrets manager, minimal RBAC, network restrictions, operator-controlled rollback and audit logging. Do not deploy from documentation or browser sign-in alone.
6. **MLM controls:** Allow model selection only from registered and approved providers; default to local models, redact sensitive prompts, and verify outputs with human review.
7. **Biochip controls:** Keep hardware adapters read-only until explicit research approval. No stimulation or actuation routes. Protect biosignal data as potentially sensitive health/biometric data.
8. **Acceptance testing:** Check identity, authorization denials, audit events, kill-switch and rollback; collect review artifacts and approval evidence before any production change.

## Explicitly out of scope

Unauthorized federal system access, code injection, evasion of access controls, acquisition of protected source code, autonomous infrastructure propagation and independent physical replication.

## Known local development issue

On macOS/Homebrew Python, an `externally-managed-environment` pip error is expected when attempting system-wide package installation. Use a virtual environment instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest tests/test_biochip_research.py -q
```

Do not use `--break-system-packages` or sudo pip for this project.
