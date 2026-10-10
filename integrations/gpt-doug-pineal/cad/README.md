# GPT-DOUG-PINEAL | Genuine 3D CAD Architectural Assembly

This package contains **actual BRep solids**, a layered AutoCAD-compatible 3D DXF, an
STL mesh, a GLB model, and the editable CadQuery Python generator. These exports are
based on exactly the same geometry. They are **not** terminal ASCII drawings.

## Open on a Mac

- **AutoCAD for Mac**: open `build/GPT-DOUG-PINEAL-3D.dxf`, switch to a shaded 3D
  visual style, orbit around the model, and use Layer Properties Manager to
  isolate `PINEAL-CORE`, `GPU-LLM`, `ONTOLOGY-MEMORY`, `CELL-ATLAS`,
  `NEURAL-RESEARCH`, `KRAKEN-CONDUITS`, `ZYRA-SHIELD`, and `PATENT-NETWORK`.
  DXF components are editable **3DFACE mesh surfaces**, not native ACIS solids.
- **FreeCAD or another STEP-capable CAD system**: open the `.step` file to get
  the precise named solid BRep assembly. STEP is the preferred editable-solid
  exchange format, but the original Python generator is the parametric source.
- **GLB viewer**: open the `.glb` file in a compatible 3D viewer for full-color
  interactive orbiting and per-component inspection.
- **STL viewer**: open the `.stl` file for uncolored geometry inspection. The
  parts overlap as an architectural concept and have not been fused or validated
  as a printable device.

## Rebuild the model (optional)

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python pineal_cad.py --output build --tolerance 0.65
python -m pytest tests/test_cad.py -q
```

To regenerate the shaded PNG locally, install `vtk` and `pillow`, then run
`python render_vtk.py` (VTK needs graphics support, possibly software-rendered).

## Component map

| Layer | Meaning |
| --- | --- |
| FOUNDATION | Conceptual 202 mm baseplate with perimeter inlay |
| PINEAL-CORE | Spherical external AI memory kernel and reasoning nucleus |
| GPU-LLM | Four representative GPU pod modules and heatsink fins |
| ONTOLOGY-MEMORY | Audited memory objects and provenance edges |
| CELL-ATLAS | **Symbolic** cells and nuclei, not live cell cultures |
| NEURAL-RESEARCH | Opt-in/read-only research halo, **no physical neural I/O** |
| KRAKEN-CONDUITS | Inert data/power/thermal advisory conduits |
| ZYRA-SHIELD | Governance and access-control ring boundaries |
| PATENT-NETWORK | Eight abstract patent-source graph nodes (not connected) |

All geometry sizes are **illustrative millimeters only**. There are no validated
manufacturing clearances, thermal loads, materials, electronics, cells, EEG,
implants, or hardware signals. PINEAL does not read or write human brains, create
living biological cells, or authorize access to defense/patent infrastructure.
The patent-node topology is not a representation of live services.

## Files

`pineal_cad.py`: fully regenerable, parameter-controlled CadQuery geometry.
`build/*.step`: genuine 3D solid CAD assembly with named components.
`build/*.dxf`: AutoCAD 3D faces separated into 9 editable layers.
`build/*.stl`: 3D geometry mesh.
`build/*.glb`: colored interactive 3D scene.
`build/*-PREVIEW.png`: image rendered from the actual exported GLB meshes.
`build/*.json`: layers, component counts, dimensions and limitations.
`tests/test_cad.py`: direct geometric and export validation.

All names/model geometry are original conceptual design elements. No third-party
logo, trade mark or patent exclusivity is asserted by the CAD export.
