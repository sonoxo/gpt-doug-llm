# XUNIA / Zyra priority repairs

These changes connect separate repositories through a versioned route-receipt contract. They do not merge the repositories or claim a live deployment.

## Priority results

| Priority | Change | Remaining limit |
| --- | --- | --- |
| 1: Registration | Safehouse is bound to the kernel, ecosystem registry, and RVIA planning adapter; its vocabulary maps to canonical types. | Training ingestion, analysis, and human review are still planned steps. |
| 2: Contracts | Identical versioned `packages/mission-contract` packages define and validate route receipts in GPT-Doug, Zyra, and XUNIA. The integration check detects drift. | This is a route-evidence contract, not a replacement for every service API. |
| 3: Permissions | Zyra planning requires owner/admin role; manifests validate runtime fields, time windows, limits, targets, and exclusions. Plans retain their authorization window and scope. | These checks govern plan generation. Each executor must independently authorize actual execution. Existing live-implement action endpoints need a separate authentication review before exposure. |
| 4: Evidence | Planning returns PLANNED; remote contract handoff returns ACCEPTED. Exceptions produce audited FAILED records. XUNIA rejects unsupported completion claims and older receipt overwrites. | Imported receipts are explicitly unauthenticated and execution-unverified; validation is not a digital signature. |
| 5: Connections | RVIA has read-only status adapters for GeoVision and XUNIA Chain. XUNIA's runtime imports route results into its searchable ontology. | No configured remote services were tested. No model inference, Foundry write, chain transaction, or training execution is claimed. |
| 6: Verification | Local integration tests cover routing, ledger persistence, receipt validation, and ontology consumption; CI workflows and repeatable commands are included. | Full application builds and existing FastAPI/pytest suite could not run in this environment because dependencies were unavailable. Remote CI and deployment must still be checked. |

## Roles

GPT-Doug hosts RVIA orchestration and its durable mission ledger. Zyra owns the inspected security planning and receipt-validation surfaces. God's Eye View XUNIA / Glass Onion presents the spatial ontology and imported route evidence. XUNIA Hub remains a separate infrastructure application and is not changed in this patch.

## Read-only adapters

- Target `GEOVISION`, capability `status`: operator configuration `ZYRA_LIVE_BASE_URL`; GET `/api/va3lm/geovision/status`.
- Target `XUNIA_CHAIN`, capability `status`: operator configuration `XUNIA_CHAIN_BASE_URL`; GET `/health`.
- Both use fixed paths, bounded responses, a three-second timeout, no redirects, and no mission-supplied URL. Missing configuration returns HOLD / SERVICE_UNCONFIGURED.
- Safehouse target: `SAFEHOUSE_EVERYDAYSPY_TRAINING_V1`, classification `public`, capability `planning`. This adapter returns a validated plan only.

## Receipt consumption

Zyra's authenticated POST `/api/xunia/security/route-receipt` validates an RVIA response and returns its normalized receipt without storing it or granting execution permission.

XUNIA exposes `runtime.importMissionResult(reply)` and `window.__xuniaImportMissionResult(reply)` after ontology initialization. Imported receipts appear in the ontology console with their status and execution-unverified label. They can also be exported with the existing graph JSON action.

## Verification

With the three repositories in sibling directories, run from GPT-Doug:

```sh
PYTHONPATH=va3lm/src python -m unittest discover -s va3lm/tests -p 'test_*integration.py' -v
node scripts/verify_xunia_zyra_integration.mjs
```

The cross-repository check accepts `ZYRA_REPO_PATH`, `XUNIA_REPO_PATH`, and `PYTHON` overrides. It checks identical contract files, produces real local RVIA results, reopens the SQLite ledger, validates them through Zyra's package, and imports them into XUNIA's ontology.

Zyra and XUNIA expose `npm run test:mission-contract`. The GPT-Doug workflow can run cross-repository verification manually using explicit Zyra and XUNIA refs. Draft branch checks verify their own changes without depending on unmerged peer branches.
