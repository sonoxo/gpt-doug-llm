# Security

**UNCLASSIFIED - NO CUI**

This Repo One seed is a read-only analytics microservice.

Security properties:

- no hardware-write or stimulation interface;
- no outbound HTTP client in the request path;
- no persistent data store;
- request body limited to 1 MiB;
- analysis bounded to 10,000 frames and 256 channels;
- strict integer spike-count validation;
- fixed provenance-label allowlist;
- non-root container user;
- explicit health and readiness endpoints;
- no request-body logging.

Do not submit secrets, credentials, CUI, PHI, PII, export-controlled data, or
classified material to this public seed project.

Authentication and authorization should be applied by the approved Platform One
deployment architecture. Do not treat unverified forwarding headers as identity.
