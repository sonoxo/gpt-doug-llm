# Security Model

THE NORTH STAR FEDERATION is a coordination and governance layer. It does not grant authority by itself.

## Security invariants

- Default external mutation is denied unless explicitly enabled and authorized.
- Material actions require the configured human authority path.
- Members should receive least-privilege, revocable capabilities.
- Evidence and provenance are required for consequential decisions.
- Safe simulation, dry-run, staging, or rollback is preferred before material changes.
- Unknown or malformed federation actions fail closed.
- Secrets belong in an external secrets manager or authorized runtime, not in the federation registry.
- Model confidence is never accepted as proof of authorization.
- Self-reported agent success is not sufficient verification.

## External integrations

The federation may describe integration adapters for systems such as GitHub or authorized Palantir Foundry/AIP environments. Those external systems remain authoritative for authentication, licensing, permissions, tenancy, and audit requirements.

## Defense-adjacent boundary

Allowed live domains include readiness, logistics, maintenance, defensive cybersecurity, communications resilience, infrastructure resilience, sensor health, simulation, and decision support.

Operational real-world weapon targeting, fire-control, weapons release, and autonomous engagement are outside the live-action federation layer.

## Reporting

For security findings in a federation member, report the issue to that member's canonical repository and follow its security policy. For federation-registry problems, open an issue with reproduction steps and avoid publishing secrets or private credentials.
