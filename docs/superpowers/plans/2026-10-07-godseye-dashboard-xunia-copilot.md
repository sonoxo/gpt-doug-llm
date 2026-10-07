# GoDsEye Dashboard and XUNIA Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build a unified read-only GoDsEye dashboard and embed the same GPT-Doug query/planetary planning experience into the XUNIA Planet wrapper.

**Architecture:** Keep the existing static-HTML pattern used by global-intel and BioFusion dashboards. The dashboard and XUNIA copilot both call the GoDsEye/planetary API from the core plan; neither surface executes shell commands or real-world actions.

**Tech Stack:** FastAPI static routes, HTML/CSS/vanilla JavaScript, Fetch API, WebSocket, pytest static/route tests.

**Spec:** docs/superpowers/specs/2026-10-07-gpt-doug-planetary-godseye-design.md

## Global Constraints

- Observation/recommendation surfaces only.
- Existing focused dashboards remain available and linked.
- No browser-side secrets, API keys, arbitrary shell execution, implant control, weapon control, vehicle control, or destructive actions.
- Provenance, degraded-source state, uncertainty, compliance warnings, and policy boundaries must be visible.
- XUNIA/MMGIS iframe messages are accepted only from https://xunia-mmgis-forge.onrender.com.
- The copilot sends only explicit operator queries plus visible authorized map context.

## Review Focus

- Partial/degraded snapshots must render without breaking the page.
- WebSocket disconnects must not erase the last successful REST snapshot.
- Provenance strings containing HTML must render as text only.
- Untrusted iframe origins must be ignored.
- API outage in the XUNIA wrapper must show OFFLINE and must not silently fall back to another service.

---

### Task 1: GoDsEye dashboard route and shell

**Files:**
- Create: agency_cloud/static/godseye.html
- Modify: agency_cloud/app.py
- Test: agency_cloud/tests/test_godseye_ui.py

**Interfaces:**
- Consumes GET /api/v1/godseye/status
- Consumes GET /api/v1/godseye/sources
- Consumes GET /api/v1/planetary/status
- Consumes WS /ws/v1/events
- Produces GET /godseye
- Required DOM IDs: coreState, systemHealth, brainState, warhawkState, zyraState, intelState, complianceState, bioState, planetaryState, policyState, provenanceList, eventLog, queryInput, querySubmit, queryOutput.

- [ ] Step 1: Write a failing route/structure test asserting GET /godseye returns 200, all required IDs exist, and links to /global-intel, /global-compliance, and /bioinformatics-fusion are present.
- [ ] Step 2: Run pytest agency_cloud/tests/test_godseye_ui.py::test_godseye_dashboard_route_and_structure -v; expected FAIL.
- [ ] Step 3: Implement the route and static page shell using the existing single-file dashboard style.
- [ ] Step 4: Re-run the structure test; expected PASS.
- [ ] Step 5: Commit the route, page, and test.

### Task 2: Dashboard live rendering and query flow

**Files:**
- Modify: agency_cloud/static/godseye.html
- Test: agency_cloud/tests/test_godseye_ui.py

**Interfaces:**
- Consumes POST /api/v1/godseye/query with JSON body containing question.
- Produces loadSnapshot() -> Promise<void>
- Produces submitQuery() -> Promise<void>
- Produces connectEvents() -> void
- Produces setText(id, value) -> void for all operator-controlled output.

- [ ] Step 1: Add failing static-behavior tests asserting the page fetches all required REST endpoints, posts to /api/v1/godseye/query, and opens /ws/v1/events.
- [ ] Step 2: Add failing safety assertions prohibiting eval, new Function, arbitrary terminal/shell execution strings, and raw HTML rendering of query/provenance values.
- [ ] Step 3: Run pytest agency_cloud/tests/test_godseye_ui.py -k "live or safe or provenance" -v; expected FAIL.
- [ ] Step 4: Implement REST loading, subsystem cards, policy state, provenance list, degraded-state rendering, and WebSocket reconnect while retaining the last snapshot.
- [ ] Step 5: Implement query form with pending-state disable, blocked-response rendering, provenance, and uncertainty.
- [ ] Step 6: Add the Review Focus test using a provenance fixture such as <img src=x onerror=1>; require textContent-only output paths.
- [ ] Step 7: Run pytest agency_cloud/tests/test_godseye_ui.py -v; expected PASS.
- [ ] Step 8: Commit dashboard live behavior.

### Task 3: XUNIA Planet in-map GPT-Doug copilot

**Files:**
- Modify: docs/planet/index.html
- Test: tests/test_xunia_planet_copilot.py

**Interfaces:**
- Consumes the existing xunia:share-state postMessage from the trusted MMGIS origin.
- Consumes POST /api/v1/godseye/query.
- Consumes POST /api/v1/planetary/plan.
- Uses configurable query parameter godseyeApi with default http://127.0.0.1:8090.
- Produces DOM IDs dougPanel, dougToggle, dougQuestion, dougAsk, dougPlan, dougOutput, dougContext.
- Produces currentMapContext() -> object
- Produces askDoug() -> Promise<void>
- Produces planMission() -> Promise<void>

- [ ] Step 1: Write failing structure/origin tests asserting the panel IDs exist, default API base is local core, the message handler checks the exact trusted origin, and no new browser geolocation API call is introduced.
- [ ] Step 2: Run pytest tests/test_xunia_planet_copilot.py::test_planet_wrapper_contains_bounded_copilot -v; expected FAIL.
- [ ] Step 3: Implement the docked panel and currentMapContext using wrapper hash/share-state only.
- [ ] Step 4: Write failing tests proving untrusted origins are ignored and fetch failure produces visible OFFLINE/error state without fallback.
- [ ] Step 5: Run pytest tests/test_xunia_planet_copilot.py -k "offline or untrusted" -v; expected FAIL.
- [ ] Step 6: Implement ask/plan calls using plain JSON. Do not send cookies, local files, shell history, environment variables, or arbitrary iframe data.
- [ ] Step 7: Run pytest tests/test_xunia_planet_copilot.py -v; expected PASS.
- [ ] Step 8: Commit the XUNIA copilot changes.

### Task 4: UI integration regression gate

**Files:** no new files unless a touched-file regression is found.

- [ ] Step 1: Run:

    pytest agency_cloud/tests/test_godseye_api.py agency_cloud/tests/test_godseye_ui.py tests/test_xunia_planet_copilot.py agency_cloud/tests/test_service.py -v

Expected: PASS.

- [ ] Step 2: Run a static unsafe-primitive scan:

    grep -RniE 'eval\(|new Function|WEAPON_CONTROL|TARGET_SELECTION|implantControl[[:space:]]*:[[:space:]]*true' agency_cloud/static/godseye.html docs/planet/index.html && exit 1 || exit 0

Expected: exit 0.

- [ ] Step 3: Commit only if a regression correction was necessary.
