# Zyra security-review baseline

Zyra is designed to produce reviewable evidence, not to self-certify a deployment. A reviewer must validate the operating system, identity provider, model runtime, dependencies, deployment process, and incident-response program in addition to this code.

## Implemented controls

| Control ID | Purpose | Evidence |
| --- | --- | --- |
| `ZYRA-INPUT-001` | Reject invalid or oversized messages | Versioned audit event and tests |
| `ZYRA-POLICY-001` | Block deterministic destructive, bypass, and prompt-injection patterns | Versioned audit event and tests |
| `ZYRA-DLP-001` | Redact recognized credentials before model/display use | Versioned audit event and tests |
| `ZYRA-HITL-001` | Require human approval for consequential or external actions | Versioned audit event and tests |
| `ZYRA-AUDIT-001` | HMAC-chain content-free audit records and fail closed when local evidence cannot be written | Audit-chain verification and tests |

These controls support evidence collection for NIST SSDF secure-development reviews, the NIST AI RMF Govern/Measure/Manage functions, and OWASP guidance for prompt injection, sensitive-information disclosure, excessive agency, and logging. They do not establish compliance by themselves.

## Review procedure

1. Run `python3 -m unittest -v` and retain the result with the reviewed commit hash.
2. Run `./security_review.py` through the secure launcher environment.
3. Confirm `audit_integrity` is `verified`, `audit_hmac_enabled` and `audit_owner_only` are true, and `sink_failures` is zero.
4. Review every policy change through a pull request with an independent security approver.
5. Perform dependency, secret, static-analysis, and adversarial prompt testing in CI.
6. Document residual risks, exceptions, owners, expiration dates, recovery procedures, and incident contacts.

## Residual risks

- Regex policy checks cannot understand every adversarial or multilingual request.
- Zyra is in-process and is not a replacement for an OS or microVM sandbox.
- Optional remote telemetry delivery is not a durable external audit anchor.
- Model behavior, dependencies, and host configuration require separate assessment.
- No government authorization, security clearance, ATO, or formal certification is implied.
