# Security

## Default posture

Shaggoth Swarm is deny-by-default for external capabilities. The included mock adapter makes no network requests and the core orchestrator has no shell, browser, credential, or unrestricted filesystem tool.

## Deployment guidance

- Keep API services bound to loopback unless you add authentication and TLS.
- Store provider keys only in environment variables or a secret manager.
- Grant tools per deployment using the capability allowlist.
- Do not expose shell execution or unrestricted network access to untrusted prompts.
- Keep `max_fanout` and `max_depth` bounded to avoid runaway task creation.
- Log tool grants and model-provider changes.

## Reporting

Open a private security advisory in the hosting GitHub repository when possible. Do not include live credentials, private keys, or exploit payloads in public issues.
