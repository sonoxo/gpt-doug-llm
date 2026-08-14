# GPT Doug LLM

**EUREKA // Build anything // Keep humans in command.**

GPT Doug is a free, local-first terminal AI powered by [Ollama](https://ollama.com). It provides a bold builder personality while keeping inference and conversations on your machine.

## Zyra cyber watchdog

Zyra is an always-on, deterministic defense layer between the user and model. It:

- blocks destructive filesystem and disk commands;
- detects common prompt-injection and security-bypass phrases;
- redacts API keys, credentials, and private keys;
- requires confirmation for publishing, deletion, transfers, purchases, and network commands;
- writes content-free audit events containing timestamps, verdicts, reasons, and SHA-256 hashes;
- stores its local audit log with owner-only permissions at `~/.gpt-doug/zyra-audit.jsonl`.

Zyra provides defense in depth. It does not replace operating-system sandboxing, least-privilege credentials, dependency scanning, or professional security review.

## Compliance gate

GPT Doug applies a conservative, jurisdiction-aware baseline using verified operational context—not sensitive identity traits. Configure only claims your deployment can verify:

```bash
export GPT_DOUG_JURISDICTION="US-NY"
export GPT_DOUG_ORG_TYPE="individual"       # individual, company, government
export GPT_DOUG_ROLE="user"
export GPT_DOUG_AGE_VERIFIED="true"
export GPT_DOUG_GOV_AUTHORIZED="false"
export GPT_DOUG_HUMAN_OVERSIGHT="true"
```

The gate blocks autonomous weapons/targeting, social scoring, protected-trait inference, and deceptive civic impersonation. Government and high-impact use requires verified authorization and recorded human review. Race, religion, gender, disability, sexual orientation, ethnicity, and similar protected traits are never accepted as access-control inputs.

This code is a technical baseline—not legal advice, government authorization, certification, or a guarantee of global compliance. Deployers must maintain a current jurisdictional policy register, complete impact assessments, obtain counsel, and independently validate controls. The design is informed by the NIST AI RMF's Govern/Map/Measure/Manage lifecycle and its Generative AI Profile.

## Required three-factor access

GPT Doug refuses to start unless an administrator or identity provider supplies three verified factors: an approved business email, an E.164 telephone number, and a Google Authenticator-compatible TOTP secret. Free consumer email domains are rejected.

```bash
export GPT_DOUG_VERIFIED_BUSINESS_EMAIL="builder@example.com"
export GPT_DOUG_ALLOWED_EMAIL_DOMAINS="example.com"
export GPT_DOUG_VERIFIED_PHONE="+12125550123"
export GPT_DOUG_TOTP_SECRET="BASE32SECRET"
./gpt-doug
```

The secret should be provisioned to Google Authenticator through your identity provider. Never commit it or store it in shell history. The CLI validates identity claims but does not send email or SMS; production deployments must obtain those verified claims from an IdP with phishing-resistant MFA, rate limiting, recovery controls, and session revocation.

### Optional Palantir Foundry governance bridge

Zyra can send metadata-only policy events to an administrator-provisioned Foundry ingestion or Action endpoint. It never exports prompts, responses, credentials, or content hashes, and it cannot receive commands from Foundry.

```bash
export FOUNDRY_SECURITY_ENDPOINT="https://your-stack.palantirfoundry.com/your-approved-ingestion-endpoint"
export FOUNDRY_ALLOWED_HOST="your-stack.palantirfoundry.com"
export FOUNDRY_TOKEN="your-short-lived-token"
./gpt-doug
```

For production, use a least-privilege OAuth2 client managed by the Foundry administrator. Never commit tokens. The bridge is intended for authorized cybersecurity governance and incident auditing—not weapons, targeting, or autonomous combat decisions.

## Quick start

1. Install Ollama and download a supported model:

   ```bash
   ollama pull llama3.2
   ```

2. Create GPT Doug:

   ```bash
   ollama create gpt-doug -f Modelfile
   ```

3. Launch:

   ```bash
   ./gpt-doug
   ```

## Commands

- `/help` — show commands
- `/clear` — clear conversation memory
- `/mission` — display the operating principles
- `/zyra` — show watchdog status
- `/compliance` — show declared compliance context
- `/quit` — exit

## Principles

1. Build useful things.
2. Explain important decisions.
3. Protect user data.
4. Ask before destructive or external actions.
5. Keep humans in command.

## EUREKA cooperative language

`EUREKA/1.0` is GPT Doug's compact JSON protocol for AI systems helping each other without bypassing controls. It supports six explicit signals: `HELLO`, `PLAN`, `REQUEST`, `EVIDENCE`, `DECISION`, and `HANDOFF`.

Every message includes sender, recipient, purpose, payload, human/service authorization, timestamp, and a unique ID. Messages are limited to 32 KiB and remain subject to Zyra inspection and the compliance gate. EUREKA does not grant tools, permissions, identity, or authority by itself.

```python
from eureka import EurekaMessage, Signal

message = EurekaMessage.create(
    Signal.REQUEST,
    sender="gpt-doug",
    recipient="review-agent",
    purpose="review a proposed patch",
    payload={"commit": "abc123"},
    authorized_by="project-owner",
)
print(message.to_json())
```

## EUREKA 369 Dev Terminal

Enter `/eureka 369` inside GPT Doug to request a constrained developer session. The phrase is not a password and grants nothing by itself. Elevation requires:

- successful startup 3FA;
- `GPT_DOUG_ROLE=developer` or `GPT_DOUG_ROLE=admin`;
- a fresh Google Authenticator code;
- a Zyra audit event.

The terminal supports only `status`, `test`, `audit`, `config`, `help`, and `exit`. It has no arbitrary shell, code evaluation, file mutation, secret display, network operation, permission change, or security-control bypass.

### ASTRAL — S.AGI × Q

ASTRAL is the fail-closed high-assurance layer above EUREKA 369. It requires an independent security officer with a separate business identity, phone, and Google Authenticator secret; enforces two-person approval; caps elevated sessions at five minutes and 20 commands; locks authorization after repeated failures; and HMAC-chains Zyra audit records using a key of at least 256 bits.

```bash
export ASTRAL_SECURITY_OFFICER_EMAIL="security@example.com"
export ASTRAL_SECURITY_OFFICER_PHONE="+12125550124"
export ASTRAL_SECURITY_OFFICER_TOTP_SECRET="SEPARATEBASE32SECRET"
export ASTRAL_AUDIT_HMAC_KEY="$(openssl rand -base64 32)"
```

Store these values in a managed secret store—not source code or shell history. ASTRAL is an unclassified engineering baseline, not a Top Secret accreditation, clearance, authorization to operate, or substitute for an accredited government environment.

## License

MIT. GPT Doug is an independent open-source project.
