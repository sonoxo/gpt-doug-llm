# CL1 MOLECULAR OBSERVATORY / ATOM → MOLECULE → COSMOS

**Live target after GitHub Pages deployment:** https://xunia.org/molecules/

A **free and non-kinetic** interactive molecular topology viewer integrated into XUNIA HQ, NASA/JPL COSMOS, the CL1 Biological Data Center, and the Fusion Atlas.

## Scientific scope

A complete list of **all observable molecules** does not exist: molecular space includes vast and evolving classes of structures, multiple conformers and ions, and many compounds have not been measured or detected. A PubChem record establishes a chemical structure/identity, **not an astronomical detection**. A spectral line entry supplies transitions used for identification, **not proof of observation in a specific astronomical source**.

This release contains **33 manually curated illustrative models**, 180 explicit atom instances and 148 bonds. They span elements H/C/N/O/S/P/Cl/F and include water, methane, ammonia, carbon monoxide, hydrogen cyanide, methanol, benzene, urea and glycine. The frontend recognizes **all 118 element symbols**, enabling additional bounded imports with other elements.

There are two evidence labels:

- `chemistry-reference`: a formula/connectivity teaching model or a CID-backed PubChem import, with **no astronomical detection claim**.
- `astronomical-reference`: a selected familiar molecule linked to a relevant astronomy spectroscopy database. This is a **catalog-level reference**, not confirmation of any detection at a particular sky position or wavelength.

**3D viewer geometry is procedural and illustrative**, not experimental atomic positions, energy-minimized structures, high-quality force-field conformers, molecular dynamics, electronic structure computations, or spectral reconstructions. Basic bond-order lines and element colors are visualization aids only. The generic bond representation does not model resonance, tautomerism, isotopes, stereochemistry, formal charges or coordination compounds comprehensively. PubChem 2D structure imports often omit explicit hydrogens; the authoritative formula is shown separately.

## Working controls

- Search compounds by name, formula, ID, family or element; filter astronomy-linked examples and chemical references independently.
- Rotate the illustrated 3D atom-bond viewer with mouse/touch drag; wheel and buttons zoom; select an atom to see its element, atomic number, approximate atomic mass (when bundled) and bond neighbors.
- Switch between **ball-and-stick**, **space-fill** and **wireframe** visual modes. Rotation speed and pause, with reduced-motion support.
- Click atoms in the 2D molecular bond graph. Inspect counts, mass, source status, formula and record provenance.
- **SAVE VIEW PNG** exports the currently visible Canvas view. **EXPORT STRUCTURE JSON** exports the selected atom/bond record locally.
- **RUN SELF-TEST** or `/health` checks the loaded catalogs and rendered atom/bond graph.
- **Cmd/Ctrl+K** focuses a finite UI console: `/find water`, `/select Benzene`, `/mode space`, `/speed 48`, `/next`, `/pause`, `/play`, `/capture`, `/export`, `/health`, `/reset`. No shell or physical devices.
- No runtime external requests: the public page fetches only the two versioned same-origin JSON files (`catalogs/seed.json`, `catalogs/pubchem.json`). It makes no network calls to PubChem, NASA, CDMS, AWS or Palantir from the browser.

## Expand the catalog: free PubChem PUG REST importer

**PubChem PUG REST is a public NCBI service, subject to rate limits and fair usage.** The importer performs bounded explicit CID downloads from your Mac using Python stdlib, no API keys. It fetches compound properties and **2D** atom/bond records, validates CID, element numbers, bond types, coordinates, limits and provenance, then atomically writes a local JSON catalog. It fails closed on unsupported bond types rather than inventing structure.

Example:

```bash
cd ~/xunia-xenology-live
git pull --ff-only
python3 scripts/xunia_molecules_import.py --cid 962 --cid 297 --cid 241 --limit 3
```

These example CIDs correspond to common molecules but **must be confirmed by the API during import**. Imports use a minimum delay between public requests and bounded HTTP timeouts/retries. Each run accepts 1–25 unique CIDs, with a cumulative import cap of 500; records containing more than 350 displayed atoms or 600 bonds are rejected by the current viewer.

The importer writes `docs/molecules/catalogs/pubchem.json` locally. **It does not publish the downloaded data automatically**, open a pull request, run perpetually, or claim that all chemical or space molecules have been imported. The shipped import file is an explicitly empty placeholder.

For a personal local copy, use the existing COSMOS launcher:

```bash
bash scripts/xunia-cosmos
```

Open the **Molecular Observatory** under the printed port, e.g. `http://127.0.0.1:8873/molecules/`. If another COSMOS server already serves that port from a different directory, launch the newly updated copy on a free port instead.

## Authoritative public references

- [PubChem PUG REST documentation](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest): public chemical identities, formulas, properties and structure records.
- [NASA JPL Molecular Spectroscopy](https://spec.jpl.nasa.gov/): spectral line databases and research material.
- [CDMS Molecules](https://cdms.astro.uni-koeln.de/classic/molecules/): species identified/studied for astronomical spectroscopy; check exact detection sources.
- [List of Observed Interstellar Molecules](https://molecules-in.space/): dynamically updated observational inventory. This external list is **not automatically imported**, and detections can be revised.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_xunia_molecules.py' -v
python3 tests/xunia_molecules_chrome_smoke.py
node --check docs/molecules/molecules.js
```

GitHub Actions tests the curated catalog, PubChem parser, source status boundaries, routes and actual Chromium interactions alongside the previously installed Fusion/COSMOS/Planetary/Xenology suites.

## Trust boundary

No Vercel, paid APIs, secrets, chemical synthesis instructions, physical instrumentation, private laboratory feeds, autonomous collection, or live astronomy detection claims. This is a scalable **educational chemical ontology viewer**, not a substitute for PubChem, JPL spectroscopy databases, molecular quantum modeling tools, or observational astronomy pipelines.
