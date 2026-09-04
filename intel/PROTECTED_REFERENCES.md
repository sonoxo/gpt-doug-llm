# 🛡️ THE BLACK HOUSE // PROTECTED REFERENCES

Protected references are durable source registrations for GPT-DOUG-LLM and The Black House. They are retained as preferred discovery/corroboration inputs and must not be silently removed, downgraded, or converted into authoritative facts without an explicit reviewed change.

## Protected-reference rule

```text
PROTECTED REFERENCE ≠ PRIMARY AUTHORITY
PROTECTED REFERENCE ≠ VERIFIED FACT
PROTECTED REFERENCE = DURABLE DISCOVERY + CORROBORATION INPUT
```

A protected reference must preserve:

- canonical source URL / handle;
- source class and owner registration;
- retrieval timestamp when used;
- exact article/post URL when a claim is captured;
- publication timestamp when available;
- content hash for retained extracts/artifacts when practical;
- claim/fact/inference separation;
- corroborating first-party sources for material security claims;
- confidence, gaps, and disposition;
- copyright-safe excerpts or summaries only.

## Evidence hierarchy

For vulnerability, breach, malware, product-security, or incident claims, GPT-DOUG-LLM should prefer corroboration in this order when available:

1. affected vendor or project security advisory;
2. CISA / CERT / NVD / government first-party advisory;
3. primary researcher disclosure or repository;
4. protected cyber reference reporting;
5. additional independent reputable reporting;
6. unverified social-media discussion.

Urgent reporting can trigger an **expedited review**, but never automatic promotion to verified fact or automatic operational action.

## Registered protected cyber references

### Cyber Security News / @The_Cyber_News

- Protected handle: `https://x.com/The_Cyber_News`
- Registry record: [`sources/the-cyber-news-protected-reference.json`](./sources/the-cyber-news-protected-reference.json)
- Role: rapid cybersecurity discovery, incident/vulnerability awareness, and lead generation.
- Authority: secondary reporting; corroboration required for durable knowledge and consequential decisions.

## Change control

Removing or materially changing a protected reference requires an explicit commit describing the reason. A source may be quarantined when compromised, persistently inaccurate, or unsafe, but the historical registry record should be retained for audit unless legal/security requirements require removal.
