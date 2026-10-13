# GPT-Doug LLM x Official TAK Documentation and Third Party Pipeline

**Scope and evidence:** An offline, curated public-source index, not a full copy of the authenticated TAK.gov library. The logged-in Third Party Pipeline instructions were supplied by the user on 2026-10-13 and are attributed accordingly. Public technical specifications originate from official TAK Product Center GitHub source/documentation, pinned to inspected revisions.

## Implemented components

| Component | Source | Implementation |
| --- | --- | --- |
| TAK-GEO local visualization | CoT XML notes, GeoJSON, USGS | Offline markers/routes/areas and opt-in USGS raster imagery |
| Map-source catalog | sonoxo/ATAK-Maps and MOBAC XML reference | Versioned TMS/WMS/composite source metadata and provenance ontology |
| TAK documentation registry | TAK.gov reference pages, ATAK-CIV and TAK Server GitHub | Static searchable source links, domain graph and gate diagnostics |
| Authorized local manuals | User-provided local directory | Local metadata inventory, temporary text search; no upload |
| ATAK-CIV GeoAtlas plugin | sonoxo/atak-civ plugintemplate | Discoverable plugin source, offline synthetic view, reproducible third-party ZIP, CI preflight |
| TAK.gov authenticated compilation, signing and deployment | Third Party Pipeline (login required) | **Not completed or claimed** |

## References and provenance

- ATAK-CIV public source: https://github.com/TAK-Product-Center/atak-civ (pinned SHA 9f6893dd657feacc35ec5de03dad721c2e44170e)
- TAK Server public source: https://github.com/TAK-Product-Center/Server (pinned SHA 5187abd46d827d37cfc5708805eced197a837e49)
- ATAK-Maps: https://github.com/sonoxo/ATAK-Maps (pinned SHA 9dd45641a6849bf52e56b279e39b27126573c434)
- TAK.gov resources: https://tak.gov/documentation/resources (authenticated contents not mirrored)
- Third Party Pipeline: https://tak.gov/user_builds (authenticated)
- Third Party Pipeline agreement: https://tak.gov/user_builds/agreement
- Civilian plugin implementation: https://github.com/sonoxo/atak-civ/pull/1
- Source-package CI: https://github.com/sonoxo/atak-civ/actions/runs/38393316154
- Map atlas review: https://github.com/sonoxo/gpt-doug-llm/pull/360

## Third Party Pipeline requirements from the supplied official page

1. Package source as a ZIP containing one root directory (GPTDougGeoAtlas). Include Gradle scripts and wrapper at that root.
2. Declare a Gradle assembleCivRelease target.
3. Resolve all SDK artifacts using atak-gradle-takdev. The supplied pipeline text specifies 2.+ for ATAK >=4.2; the inspected ATAK 5.6.0 plugin template specifies 3.+. **Version compatibility is unresolved until authenticated SDK compilation.**
4. Use a unique ProGuard class descriptor and the com.atakmap.app.component manifest activity/action for plugin discovery.
5. Validate the full Gradle release build using authorized TAK artifact credentials. No credentials may appear in GitHub or the source ZIP.
6. After review, accept the participation terms and submit source ZIP in the logged-in TAK.gov Third Party Pipeline. Signing is not the same as official TPC production certification or operational transition.

## Launch the documentation viewer locally

Run these from your existing gpt-doug-warfighter checkout on the documentation feature branch.

~~~bash
python3 -m tak_geo docs-status
python3 -m tak_geo docs-build --output build/tak-docs
open build/tak-docs/docs.html
~~~

For authorized, separately downloaded manuals, keep files in a private local folder:

~~~bash
python3 -m tak_geo docs-inventory --local-root "$HOME/TAK-authorized-docs"
python3 -m tak_geo docs-find --local-root "$HOME/TAK-authorized-docs" --query Gradle
~~~

These commands never download TAK.gov manuals, persist a search index, or send contents to a remote service. The document registry is a source-pointer catalog, not an authenticated wiki mirror.

## Release and future phase acceptance gates

| Phase | Status | Exit condition |
| --- | --- | --- |
| Public documentation + provenance graph | Built | CI green and regular revalidation |
| Synthetic geospatial viewer + provider catalog | Built | Local user review and licensed map sources |
| Third Party Pipeline source ZIP | Built; static CI passed | Format proof, verified hashes, no credentials |
| Authenticated Gradle assembleCivRelease | Blocked by authorized developer access | Actual successful release build and dependency resolution |
| TAK.gov Third Party Pipeline submission | Not submitted | User accepts terms and uploads reviewed ZIP |
| Government third-party signing and on-device test | Not signed/tested | Official build results and supported-device testing |
| Future civilian ATAK geospatial extension | Planned only | Licensed map integration, usability and security review |
| Future TAK Server interoperability | Not implemented | Separately approved credentials, security/ATO and test plan |

This system does not claim access to live TAK clients, restricted maps, operational telemetry, or government systems. Public code access and authorized operational deployment are separate matters.
