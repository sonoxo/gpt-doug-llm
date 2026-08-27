# ZYRA Intelligence Access Control Plan

## Command principles
- Least privilege and role separation govern every deployment.
- Agent Core remains bounded to allowlisted repository actions; arbitrary shell, push, deploy, send, secret access, and third-party targeting are outside the autonomous action set.
- Privileged administrative access must use deployment-level strong authentication and MFA where required.
- Shared privileged accounts are prohibited unless a target authority explicitly permits and controls them.
- Access reviews must be recorded on a recurring schedule appropriate to the deployment baseline.
- Service identities receive only the permissions required for their assigned intelligence function.

## Roles
- INTELLIGENCE_OPERATOR: read/query approved intelligence and run bounded analysis.
- INTELLIGENCE_CURATOR: ingest and classify intelligence with provenance.
- COMMAND_REVIEWER: approve high-impact intelligence promotion.
- PLATFORM_ADMIN: maintain runtime and deployment configuration.
- SECURITY_AUDITOR: read security evidence and audit trails without routine modification rights.

## Command evidence required at deployment
Identity provider configuration, MFA enforcement, role mapping, privileged-access inventory, account lifecycle evidence, periodic review records, session controls, and remote-access restrictions.
