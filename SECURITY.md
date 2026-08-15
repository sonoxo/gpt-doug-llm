# Security Policy

## Supported Versions

GPT Doug LLM is actively developed. Security fixes apply to the latest `main` branch.

## Reporting a Vulnerability

DO NOT open a public GitHub issue for security vulnerabilities.

Instead, email: security@sonoxo.com with:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

You will receive a response within 72 hours. If the vulnerability is confirmed, a fix will be released and you will be credited (unless you prefer to remain anonymous).

## Zyra Security Model

GPT Doug uses a defense-in-depth architecture:

| Layer | Module | Purpose |
|---|---|---|
| 1 | Zyra 3.0 | Input/output inspection, secret redaction, block patterns |
| 2 | Golden Shield | Perimeter defense, threat elimination, rate containment |
| 3 | Zyra Sentinel | 24/7 vulnerability scanning, threat intel feeds |
| 4 | Compliance Gate | Jurisdiction-aware policy enforcement |
| 5 | Three-Factor Auth | Business email + phone + TOTP |
| 6 | ASTRAL | Two-person high-assurance elevation control |
| 7 | EUREKA 369 | Constrained developer terminal (allowlisted commands only) |

**Zyra is deterministic, not semantic.** It catches known attack patterns. Novel attacks that don't match known patterns may pass. OS-level sandboxing, least-privilege credentials, container isolation, and professional security review are still required.

## Audit Trail

All security decisions are written to a tamper-evident HMAC-chained audit log at `~/.gpt-doug/zyra-audit.jsonl` (owner-only, 0600 permissions). Verify integrity with:

```bash
python3 security_review.py
```

## Known Limitations

- No third-party security audit has been performed
- No formal compliance certification (SOC2, FedRAMP, CJIS, NIST 800-53)
- No load/stress testing at scale
- Zyra is keyword/pattern-based, not a semantic understanding system
- Single-machine deployment (no redundancy, failover, or monitoring beyond local logs)
- Agent-daemon retry logic has no automated regression tests

## Responsible Disclosure

We follow responsible disclosure. Security researchers who report valid vulnerabilities will be acknowledged in release notes (unless they prefer anonymity).
