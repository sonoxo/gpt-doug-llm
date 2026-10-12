# GPT-DOUG / Palantir ecosystem — visual source graph

This module transcribes names and visual groupings from a user-provided infographic titled **The Palantir Ecosystem**, bearing an **ODM** mark. The infographic is **not independent evidence** that any depicted organization has a contract, partnership, political affiliation, investment, client relationship, access credential, or endorsement. The source image itself is not redistributed in this repository.

## Working interfaces

- Browser: with the existing ZYRA Intelligence Cloud running, open `http://127.0.0.1:8080/assets/palantir-ecosystem.html`. The asset also works under `python3 -m http.server 8080 --directory agency_cloud/static` at `/palantir-ecosystem.html`.
- Read-only data: `agency_cloud/static/palantir-ecosystem-data.json` (one canonical transcription).
- Python projection: `python3 -m zyrapalantir.ecosystem_intelligence status` or `python3 -m zyrapalantir.ecosystem_intelligence graph`.
- Review-only ontology records: `python3 -m zyrapalantir.ecosystem_intelligence ontology`.
- Validate: `python3 -m unittest tests.test_palantir_ecosystem_graph -v`.

The graph contains `diagram_focus`, `diagram_group`, and `named_in_diagram` objects with `graphic_layout_context` and `graphic_group_membership` links. **Every link** carries `claim_status=unverified_visual_depiction` and the single graphic's `source_id`. It makes no entity-to-entity factual inference. The graphic's color/legend categories are retained as design metadata only, not a finding about any organization.

## Governance and safety

- Offline read-only: no scanning, injection, remote authentication, outbound telemetry, Palantir API calls, or external writes.
- No implication of Palantir Foundry/AIP/Gotham/OSDK tenant access, collaboration agreement, government authorization, accreditation, or contractor status.
- `ontology` produces **review-only JSON**; it never creates tenant objects or invokes Foundry actions.
- Source SHA-256 is recorded for comparison if the original file is obtained legitimately; source verification remains `unverified` until backed by independently assessed evidence. Do not promote graph edges based on visual proximity.
- To support future verified claims, add a separate, access-controlled evidence review workflow with primary citations, event dates, counterevidence, review status, and per-claim provenance. Keep unverified graphics isolated from production decision inputs.

This is a source-research addition to ZYRAPALANTIR, **not** the simulation-control graph and **not** an external-system integration. Existing ZYRAPALANTIR safety boundaries remain unchanged.
