# XUNIA COSMOS // CL1 OUTER SPACE ONTOLOGY

**Public target after merge and Pages deployment:** https://xunia.org/cosmos/  
**Infrastructure:** GitHub Pages static HTML/CSS/Canvas + Python 3 for opt-in data import. No Vercel, paid services, API keys or browser telemetry.

## Scope and scientific accuracy

XUNIA COSMOS is an astronomical **knowledge graph**, not a clone of all outer space. The observable universe is not fully mapped, and the number of cataloged objects changes. This first version includes 55 curated entities and 54 relations, across Solar System objects, notable stars, exoplanets, galaxies, black holes, nebulae, cosmic structures, and missions. NASA/ESA importers let operators add bounded catalog subsets using public TAP interfaces.

**3D positions are schematic; neither astronomy coordinates nor physical distances are shown to scale.** Animated cosmic signals and stars are UI effects, not real physical telemetry. The app is not a telescope pointing, orbit prediction, ephemeris or spacecraft-navigation tool.

## Launch on Mac — free terminal command

Clone into a separate folder to avoid overwriting other GPT-DOUG working trees.

    cd "$HOME"
    git clone --depth 1 --single-branch -b feat/xunia-cosmos-outer-space-ontology-20261117 \
      https://github.com/sonoxo/gpt-doug-llm.git xunia-cosmos
    cd ~/xunia-cosmos
    bash scripts/xunia-cosmos

Open http://127.0.0.1:8872/cosmos/. Existing CL1:8787, Jukebox:8844 and XUNIA Bio:8871 are unaffected. For later runs: cd ~/xunia-cosmos && git pull --ff-only && bash scripts/xunia-cosmos.

## Controls

Click any celestial node for its type, parent, source, and available sourced data. Drag to orbit, scroll to zoom, use the category filters, connected entity buttons, search, and camera controls. Canvas keyboard: arrows rotate, Tab cycles visible objects, Enter focuses, slash opens search. The site labels incomplete or unimported catalogs.

## Non-kinetic interactive lab

The COSMOS viewport includes a **browser-only simulation lab**. Select a cataloged object by clicking, searching, or using the command console. Choose **OBSERVE**, **SIGNAL WAVES**, **GRAVITY LENS**, or **FIELD LINES**; adjust the intensity slider; pause/resume field animation. These are *illustrative* effects, not real electromagnetic, gravity or radio propagation calculations.

Use **Ctrl+K** (or **Cmd+K** on macOS) to focus the command console, and **Escape** to return to the spatial view. Supported console commands include:

- `/go Andromeda` — select and center the matching cataloged object
- `/mode signal`, `/mode gravity`, `/mode field`, `/mode observe`
- `/power 75` — illustrative field intensity from 0–100
- `/orbit 45` — rotate the *camera* by degrees, from −360 to +360 per command
- `/zoom 1.5` — set schematic zoom from 0.38 to 4
- `/filter galaxies`, `/filter all` — select object sectors
- `/pause`, `/play`, `/reset`, `/help`

No command is executed in a shell. The parser only changes local viewer state; there are no transmitters, actuators, devices, sensor access, external command APIs, or network calls beyond loading local static catalog JSON. Mode labels such as "signal" and "gravity" indicate *visual metaphors*, not physics engines. Reduced-motion users see static effects that still respond to controls.

## Add actual NASA/ESA catalog subsets

NASA Exoplanet Archive composite table, host stars and their cataloged planets:

    cd ~/xunia-cosmos
    bash scripts/xunia-cosmos import nasa --limit 250

ESA Gaia DR3 nearer/bright source subset:

    bash scripts/xunia-cosmos import gaia --limit 250

Limit range 1–2000; response cap 8 MiB; timeout 35 seconds. Uses public documented TAP services with no API keys. Writes atomic JSON snapshots to docs/cosmos/catalogs/nasa.json or docs/cosmos/catalogs/gaia.json. These appear in the local viewer after REFRESH LOCAL CATALOGS; they are not automatically pushed to GitHub or published. Operators must review attribution and data before committing source-generated files.

For an offline imported file:

    python3 scripts/xunia_cosmos_import.py nasa --input /path/to/nasa-tap.json --limit 250

Python importer applies bounded parsing and input validation; the browser uses textContent rather than HTML injection. External object links are restricted to recognized official NASA and ESA hostnames.

## Sources and attribution

- NASA/IPAC/Caltech Exoplanet Archive TAP: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- ESA Gaia DR3 public archive: https://gea.esac.esa.int/archive/
- NASA/JPL Solar System Dynamics reference: https://ssd-api.jpl.nasa.gov/
- SIMBAD/CDS astronomical identifier reference: https://simbad.cds.unistra.fr/simbad/

JPL Horizons and SIMBAD are references, not currently implemented data import adapters. NASA/ESA data licenses and citation rules should be reviewed before redistribution. The curated seed includes explanatory official source references, but does not imply direct per-object live verification.

## Validation

    python3 -m unittest discover -s tests -p 'test_xunia_cosmos.py' -v
    python3 tests/xunia_cosmos_chrome_smoke.py
    node --check docs/cosmos/cosmos.js
    bash -n scripts/xunia-cosmos

The real Chrome test verifies that 55 objects and 54 connections render, not just the animated background. The feature is deployed to xunia.org only after merge to main and the existing GitHub Pages workflow succeeds.

## Constraints

Free-only, no Vercel, no background network queries, no banking or vault access, no private sensor data, no invented current positions, no assertion that the observable universe has been cloned, no automatic writes to other repositories. Imported data stays operator-reviewed and source-qualified.
