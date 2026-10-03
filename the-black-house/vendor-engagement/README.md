# Black House Vendor Engagement Router

This module embeds vendor/acquisition communication routing into the Black House control plane without hardcoding live contact addresses into the public repository.

## Purpose

Resolve the smallest appropriate communication role from intent + lifecycle stage, then require the runtime to resolve the actual address from a current authorized directory, opportunity record, or private configuration.

## Canonical routing order

```text
OPPORTUNITY-SPECIFIC QUESTION
  -> OPPORTUNITY_POC

TECHNICAL / AI CAPABILITY
  -> TECHNICAL_OUTREACH

ACQUISITION PATHWAY
  -> ACQUISITION_STRATEGY

DIGITAL / FUTURE SOFTWARE CAPABILITY
  -> DIGITAL_FUTURES

VENDOR RELATIONSHIP
  -> STRATEGIC_VENDOR_MANAGEMENT

RESEARCH COLLABORATION
  -> RESEARCH_COLLABORATION

PARTNERSHIP INTERMEDIARY
  -> PARTNERSHIP_INTERMEDIARY

PERSONNEL CLEARANCE / SCI
  -> CLEARANCE_DIVISION

INDUSTRIAL SECURITY / FOCI
  -> INDUSTRIAL_SECURITY

GOVERNMENT PROPERTY
  -> CONTRACT_PROPERTY_MANAGEMENT
```

## Guardrails

- never mass-mail all contacts with the same message;
- opportunity-specific POCs outrank broad outreach channels;
- preserve address provenance and directory freshness;
- do not hardcode live contact addresses in the public repository;
- do not send classified, CUI, procurement-sensitive, credential, or private-vault material on low-side channels;
- pricing, terms acceptance, certifications, representations, and legal commitments require authorized human/business approval;
- a contact route never implies award, affiliation, clearance, authorization, or endorsement.

Canonical manifest: `vendor-engagement.manifest.json`.
