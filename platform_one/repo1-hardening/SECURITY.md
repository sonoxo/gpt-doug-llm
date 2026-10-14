# Security

**UNCLASSIFIED — NO CUI**

The hardening repository contains no application source or binary payloads.
Application inputs are checksum-pinned resources declared in
`hardening_manifest.yaml`.

Container properties:

- non-root runtime UID 1001;
- read-only analytics behavior;
- no hardware control or stimulation API;
- no request-body logging;
- no persistent storage;
- no application secrets;
- bounded request body, connection count, and socket read time;
- strict provenance-label allowlist;
- no Internet download commands in the Dockerfile;
- no `ADD` instruction;
- no Dockerfile OCI labels.

Do not submit classified information, CUI, PHI, PII, credentials, private keys,
access tokens, or export-controlled data in issues, manifests, or example
requests.

Pipeline findings should be handled through the assigned Repo One issue and VAT
workflow.
