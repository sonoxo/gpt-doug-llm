# GPT Doug Security Hardening Baseline

This document defines a **public-sector-inspired defensive baseline** for GPT Doug. It is intended to align engineering decisions with widely used public controls such as NIST SP 800-53, NIST SP 800-171, zero-trust principles, and DISA-STIG-style host/application hardening.

It is **not** a claim of U.S. Army, USMC/Quantico, DoD, DISA, FedRAMP, CMMC, FISMA, or any other government certification, authorization, accreditation, endorsement, or operational approval.

## Security objectives

1. Fail closed on authentication, authorization, audit-integrity, and provider-readiness failures.
2. Keep secrets out of source, logs, traces, model prompts, and error messages.
3. Use least privilege for processes, files, credentials, network access, and generated-code execution.
4. Separate control-plane decisions from model output.
5. Preserve tamper-evident audit evidence with owner-only permissions.
6. Require explicit human approval for consequential external actions.
7. Treat generated code and external model output as untrusted input.
8. Prefer local execution where it materially reduces data exposure.

## Public control-family mapping

| Control family | GPT Doug baseline behavior |
|---|---|
| AC — Access Control | 3FA gate, two-person elevation for high-assurance actions, least-privilege execution target |
| AU — Audit & Accountability | HMAC-chained Zyra audit trail, owner-only permissions, integrity verification |
| IA — Identification & Authentication | business identity checks plus TOTP; external provider credentials validated before use |
| SC — System & Communications Protection | explicit provider allowlist, no implicit provider discovery, network calls constrained to configured endpoints |
| SI — System & Information Integrity | Zyra policy inspection, provider readiness checks, sanitized failures, planned sandboxing of generated code |
| CM — Configuration Management | provider selection via explicit environment configuration; documented defaults and fail-safe behavior |
| RA — Risk Assessment | threat-model-driven provider and code-execution boundaries; readiness and dependency checks |
| IR — Incident Response | auditable security events and documented responsible-disclosure path |

## Provider security requirements

- `GPT_DOUG_PROVIDER=auto` may route only to providers that pass readiness checks.
- Placeholder values such as `...`, `***`, `changeme`, and short dummy strings do not count as valid credentials.
- Provider errors exposed to users are sanitized and do not include response bodies, tokens, credentials, or sensitive headers.
- Ollama is marked ready only when the daemon responds and the configured model is actually present.
- Provider order is explicit via `GPT_DOUG_PROVIDER_ORDER`.
- A provider failure must not silently disable Zyra, authentication, audit, or approval controls.

## Host hardening target

For higher-assurance deployments:

- Run the service as a dedicated non-admin account.
- Apply OS security updates promptly.
- Enable full-disk encryption.
- Restrict local audit/config directories to the owning account.
- Use a host firewall with default-deny inbound rules.
- Bind local-only services such as Ollama to loopback unless remote access is deliberately secured.
- Store production secrets in an OS keychain/HSM/secret manager rather than shell history or committed `.env` files.
- Disable core dumps for processes handling secrets where practical.
- Pin dependencies and use signed/reproducible artifacts where available.
- Run generated code only inside a separate sandbox/container/VM with CPU, memory, filesystem, process, and network limits.

## Generated-code execution boundary

Generated code is untrusted. A hardened execution layer should provide:

- non-root container/VM execution;
- read-only base filesystem;
- ephemeral writable workspace;
- process-count, CPU, memory, disk, and wall-clock limits;
- no host Docker socket;
- no host home-directory mounts;
- default-deny outbound network with explicit egress policy;
- dependency allow/deny policy and malware/dependency scanning;
- no inherited cloud/provider credentials;
- structured logs and deterministic teardown.

Until those controls are implemented and tested, generated projects should not execute automatically on the host.

## Certification boundary

Meeting portions of this baseline does not establish compliance. Real government deployment normally requires system categorization, documented control implementation, evidence collection, vulnerability management, configuration baselines, independent assessment, authorization decisions, operational monitoring, and organization-specific requirements.

The project should describe itself as **hardened toward public-sector control objectives**, not as "Army standard," "Quantico certified," "DoD approved," or equivalent unless an authorized assessment has actually granted that status.
