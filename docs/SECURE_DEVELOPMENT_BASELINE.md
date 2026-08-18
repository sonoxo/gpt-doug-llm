# Secure Development Baseline

GPT-Doug-LLM uses a public-sector-inspired secure-development baseline derived from NIST SSDF, CISA Secure by Design guidance, and NSA/CISA software supply-chain guidance.

This repository does not claim CIA, NSA, CISA, NIST, FedRAMP, FIPS, or other government certification or endorsement.

## Required controls

- Secure-by-default configuration and explicit opt-in for privileged behavior.
- Least-privilege automation and credentials.
- No secrets in source, logs, prompts, generated artifacts, or test fixtures.
- Mandatory tests and static analysis for pull requests.
- Fail-closed dependency vulnerability auditing.
- Automated dependency updates.
- Software Bill of Materials generation for reviewable builds.
- Treat model output, retrieved content, issue text, and tool arguments as untrusted input.
- Validate and normalize data at trust boundaries.
- Preserve tamper-evident audit trails for privileged actions.
- Require execution evidence before an agent may claim a tool action succeeded.
- Isolate autonomous agents from production credentials and production hosts.
- Keep humans in command for destructive, external, financial, identity, deployment, and security-sensitive actions.

## CI expectations

Security checks must not be converted to `|| true`, `continue-on-error`, or equivalent fail-open behavior unless the check is explicitly informational and documented as such.

## Supply-chain expectations

- Review direct and transitive dependencies.
- Generate and retain an SBOM.
- Prefer pinned and reproducible dependencies for release builds.
- Minimize GitHub Actions token permissions.
- Review third-party actions before use.
- Rotate credentials after suspected exposure.

## Incident response

Security findings should be triaged by severity, contained before feature work resumes, and accompanied by regression tests when a code-level fix is possible.
