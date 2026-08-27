# ZYRA Intelligence Cryptography and Key Management Plan

## Command doctrine
Cryptography claims are evidence-bound. Use of TLS, AES, OpenSSL, or a cryptography library alone does not establish FIPS 140-3 validation.

## Requirements
- Encrypt regulated intelligence in transit and at rest as required by the applicable baseline.
- Store keys outside source code and outside ordinary application logs.
- Separate key administration from routine intelligence operation where the target baseline requires it.
- Rotate, revoke, back up, recover, and destroy keys under documented lifecycle controls.
- Restrict key access to designated identities and audit administrative key events.
- Prevent secrets from entering ontology evidence, model prompts, generated reports, or Git history.

## FIPS command gate
Where FIPS 140-3 is required, production deployment must identify the exact CMVP-validated cryptographic module or validated inherited service, validation certificate, approved operating environment, runtime configuration, and key-management path. The government-intelligence fleet reports `EXTERNAL_OR_RUNTIME_EVIDENCE_REQUIRED` until that evidence is present.

## CJIS/CUI command note
If CJI or CUI enters scope, encryption and key-management requirements must be mapped to the applicable CJIS/CUI boundary and deployment architecture before activation.
