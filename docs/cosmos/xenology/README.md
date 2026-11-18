# XUNIA COSMOS / CL1 XENOLOGY + UAP + SHAGGOTH

**Public target:** https://xunia.org/cosmos/xenology/ (after merge and GitHub Pages deployment)

A free, interactive non-kinetic, desktop/mobile browser archive based on the XUNIA concept image: searchable entity cards, simulated creature viewer, UAP visual forms, source-aware research panel, visual knowledge graph, classification filters, local terminal-style commands, and downloadable JSON.

## Evidence boundary

This is an **art + research application**, **not** a list of verified alien life forms or proof that UAP are extraterrestrial.

- **ALIENS (16):** folkloric/speculative or fictional creature design archetypes. Not verified species or confirmed visitors. Labels like "Grey", "Reptilian", and "Mantis" describe popular creative depictions, not established taxonomy.
- **UAP SHAPES (10):** drawn morphology classes (saucer, triangle, cylinder, etc.) useful for visualization. They do not correspond to verified extraterrestrial vehicles, unique case findings or a scientifically established craft taxonomy.
- **SHAGGOTHS (7):** original CL1 fictional cosmic entities, built as animated conceptual procedural illustrations. Not real creatures.
- **AARO RECORDS (3):** selected public official release/case references with source links; different from hypothetical alien character art. AARO public imagery and case pages contain the actual material. If the record's status changes, the primary AARO website is authoritative.

NASA explicitly states that it has not found credible evidence of extraterrestrial life and that there is no evidence UAP are extraterrestrial: https://science.nasa.gov/uap/faqs/

Official public UAP imagery and case assessments: https://www.aaro.mil/UAP-Cases/Official-UAP-Imagery/ and https://www.aaro.mil/UAP-Cases/UAP-Case-Resolution-Reports/

The 36 objects and ontology link counts are **this project's curated entries only**. There are no fabricated claims of 312 aliens, 248 confirmed UAP, 1,842 real relationships, galactic hotspots, or live sensors.

## User capabilities

- Search by name, domain, description and ID; filter by 4 groups and 5 evidence/status labels.
- Select all 36 cards or linked graph nodes to inspect the chosen concept / report.
- Procedural Canvas concept portraits, UFO shape drawings, and Shaggoth animations (no externally fetched images).
- Drag the interactive viewer to rotate; wheel or buttons to zoom; pause motion; adjust intensity; scene tab provides explanation.
- Browser-only conceptual graph and field map. Edges mean editorial visual/theme relationships, never confirmed cosmic contact or transportation routes.
- Source-qualified overview, data, relations and simulation tabs. AARO or NASA source links require explicit user clicks and are restricted to official allowlisted hosts.
- Export the **currently filtered** data as JSON to your device; no automatic upload or persistent storage.
- Accessible keyboard controls and reduced-motion support. Cmd/Ctrl+K focuses the console; Esc returns to viewer; left/right arrows rotate the selected viewer; R chooses a random card.

### Local console commands

`/help`, `/find shaggoth`, `/select Shaggoth Prime`, `/select GOFAST`, `/group aliens`, `/group uap`, `/group records`, `/group shaggoth`, `/group all`, `/tab relations`, `/mode graph`, `/mode field`, `/intensity 80`, `/zoom 1.4`, `/pause`, `/play`, `/random`, `/export`, `/reset`.

The command console is **not a shell**; only a finite, local UI command parser.

## Full browser interaction and diagnostics

- Select any concept card to update the scene and evidence inspector; click graph nodes to navigate.
- **SAVE CURRENT SCENE PNG** exports the actual current procedural Canvas view (not official footage) through the browser's download mechanism.
- **COPY LINK TO THIS VIEW** places an explicit shareable URL with entity, inspector tab, map mode, zoom and intensity into the copy field. The link uses an allowlisted URL fragment, not local device data. Open the link again to restore the display. If browser clipboard permission is unavailable, the field is selected for manual Cmd+C.
- **RUN LOCAL SELF-TEST** or `/health` checks catalog loading, source URL restrictions, visible cards and Canvas/graph rendering. It does not check NASA/ESA imports, remote government sites or live sensors.
- COSMOS now ships explicit *unimported* NASA/ESA placeholder catalogs, avoiding 404 logs for optional archive files. These contain **zero scientific records** until you run the opt-in importer. An SVG favicon is included to avoid browser favicon 404s.

## Local Mac launch

From a new working directory to avoid overwriting a previous clone:

```bash
git clone --depth 1 https://github.com/sonoxo/gpt-doug-llm.git ~/xunia-xenology
cd ~/xunia-xenology
bash scripts/xunia-cosmos
```

Then open **http://127.0.0.1:8872/cosmos/xenology/**. The application is served by Python's standard library and requires no paid service, backend, API keys, external JS libraries, Vercel, browser telemetry or authentication.

## Architecture and security

- Public GitHub Pages static assets: `index.html`, `style.css`, `app.js`, `catalog.json`.
- Same-origin catalog fetch at startup; case reference links only open following explicit clicks. Strict HTML CSP, no arbitrary HTML injection or shell execution.
- No surveillance, live sensor feeds, classified sources, RF/radio, device actuation, banking or private files. No background research claims.
- Source records are immutable, fictional concepts remain clearly qualified, renderer uses procedural Canvas rather than unlicensed images.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_xunia_xenology.py' -v
python3 tests/xunia_xenology_chrome_smoke.py
node --check docs/cosmos/xenology/app.js
```

The Chromium test loads a temporary localhost copy of the actual app, exercises card selection, search, group filtering, inspector relations, command selection, map mode, intensity and pause; checks render counters in the browser DOM. Existing COSMOS/planet/CL1 tests run in the same GitHub Actions suite.
