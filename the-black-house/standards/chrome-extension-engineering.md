# Black House Standard — Chrome Extension Engineering

**Authority:** `THE_BLACK_HOUSE_V1`  
**Baseline:** Chrome Extensions Manifest V3  
**Primary source:** Chrome for Developers — Chrome Extensions documentation

This standard governs XuniDirect and future Black House / XUNIA / ZYRA browser extensions.

## Required invariants

- `manifest.json` exists at the extension root.
- Manifest V3 is used for production candidates.
- Background/event execution uses the Manifest V3 service-worker model where required.
- Service workers do not depend on DOM access.
- Toolbar `action`, options, or side-panel surfaces keep operator actions explicit.
- Content scripts are used only when the declared single purpose requires page-context DOM interaction.
- All executable extension logic ships in the package; no remotely hosted executable JavaScript.
- Permissions and host permissions are minimized and individually justified.
- Chrome Web Store single-purpose requirements are treated as a design constraint, not only a listing constraint.
- Consequential external mutations require visible preview and explicit human confirmation.
- Store publication and Google OAuth verification remain external evidence and are never inferred from repository state.

## XuniDirect profile

Single purpose:

> Review and manage the authenticated user's own YouTube subscriptions by subscription date or channel name, with preview and explicit confirmation before unsubscribe actions.

Preferred execution path:

`action popup -> chrome.identity -> YouTube Data API -> subscriptions.delete`

XuniDirect intentionally avoids page-click automation for unsubscribe execution because an official API path exists.

Required gate sequence:

`MISSION -> POLICY -> OWNER_AUTH -> DISCOVERY -> FILTER -> PREVIEW -> HUMAN_APPROVAL -> EXTERNAL_API_MUTATION -> RESULT -> AUDIT_EVIDENCE`

## Release evidence

A candidate may be promoted to `STORE_READY` only with evidence for:

- `MANIFEST_V3_VALID`
- `MANIFEST_AT_PACKAGE_ROOT`
- `NO_REMOTE_EXECUTABLE_CODE`
- `SINGLE_PURPOSE_DECLARED`
- `PERMISSIONS_MINIMIZED`
- `SERVICE_WORKER_VALIDATED`
- `OAUTH_CLIENT_BOUND` when OAuth is used
- `CLEAN_PROFILE_TEST_PASS`
- `PRIVACY_DISCLOSURES_RECONCILED`
- `STORE_PACKAGE_ROOT_VALIDATED`

Chrome Web Store approval remains Google-controlled external evidence.

## Truth boundary

Chrome for Developers documentation is a public first-party engineering source. Its use here does not imply Google endorsement, certification, partnership, privileged access, or Chrome Web Store approval.
