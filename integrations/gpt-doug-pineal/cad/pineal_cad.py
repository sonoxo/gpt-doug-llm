"""Parametric CAD solids for the conceptual GPT-Doug-PINEAL software architecture.

All dimensions in millimeters are *illustrative layout coordinates*, not device
specifications. No biological, EEG, implant, surgical, or military hardware is
modeled or validated. The scene is a tangible engineering diagram.

Requires CadQuery, trimesh, ezdxf, numpy (see requirements.txt).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math

import cadquery as cq
import ezdxf
import numpy as np
import trimesh


@dataclass(frozen=True)
class CADPart:
    name: str
    layer: str
    shape: cq.Shape
    rgb: tuple[int, int, int]
    purpose: str


# Colored layers preserve the semantic architecture inside STEP/GLB/DXF.
LAYERS = {
    "FOUNDATION": ((34, 48, 66), "Conceptual base and component support"),
    "PINEAL-CORE": ((189, 134, 244), "Local-first AI external-memory core"),
    "GPU-LLM": ((78, 181, 239), "GPU/LLM computation as an abstract layout"),
    "ONTOLOGY-MEMORY": ((56, 226, 194), "Audited ontology and persistent memory nodes"),
    "CELL-ATLAS": ((239, 116, 158), "Educational human-cell reference and symbolic states"),
    "NEURAL-RESEARCH": ((245, 213, 119), "Opt-in research interface; no brain I/O device"),
    "KRAKEN-CONDUITS": ((103, 167, 255), "Simulated thermal/power and governance pathways"),
    "ZYRA-SHIELD": ((45, 211, 219), "Governance, access control, defensive boundaries"),
    "PATENT-NETWORK": ((250, 166, 94), "Source-verified, licensed patent metadata graph"),
}


def _part(parts: list[CADPart], name: str, layer: str, shape: cq.Shape) -> None:
    parts.append(CADPart(name=name, layer=layer, shape=shape,
                         rgb=LAYERS[layer][0], purpose=LAYERS[layer][1]))


def _sphere(radius: float, xyz: tuple[float, float, float]) -> cq.Solid:
    return cq.Solid.makeSphere(radius, pnt=xyz, angleDegrees1=-90, angleDegrees2=90)


def _post(radius: float, height: float, xyz: tuple[float, float, float]) -> cq.Solid:
    return cq.Solid.makeCylinder(radius, height, pnt=xyz)


def _tube(radius: float, start: tuple[float, float, float],
          end: tuple[float, float, float]) -> cq.Solid:
    vector = np.array(end, dtype=float) - np.array(start, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise ValueError("tube endpoints must be distinct")
    return cq.Solid.makeCylinder(radius, norm, pnt=start, dir=tuple(vector / norm))


def _xy(radius: float, angle: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(angle), radius * math.sin(angle), z)


def build_model() -> list[CADPart]:
    """Return individually editable named BRep shapes in 9 architectural layers."""
    parts: list[CADPart] = []
    _part(parts, "Foundation_BasePlate", "FOUNDATION", _post(101, 4, (0, 0, 0)))
    _part(parts, "Foundation_PerimeterInlay", "FOUNDATION", cq.Solid.makeTorus(96, 1.2, pnt=(0, 0, 5.5)))
    _part(parts, "Foundation_InnerHub", "FOUNDATION", _post(21, 5, (0, 0, 4)))

    _part(parts, "Pineal_Kernel_BRep", "PINEAL-CORE", _sphere(18, (0, 0, 38)))
    _part(parts, "Pineal_Kernel_Halo", "PINEAL-CORE", cq.Solid.makeTorus(22, 1.7, pnt=(0, 0, 37)))
    _part(parts, "Pineal_Reasoning_Nucleus", "PINEAL-CORE", _sphere(7.2, (0, 0, 38)))
    _part(parts, "Pineal_Kernel_Bridge", "PINEAL-CORE", _post(5, 12, (0, 0, 9)))

    # Four abstract GPU cards and raised memory fins arranged around core.
    for i in range(4):
        a = (i + .5) * (math.pi / 2)
        x, y, _ = _xy(38, a, 0)
        _part(parts, f"GPU_Pod_{i+1:02d}", "GPU-LLM",
              cq.Solid.makeBox(18, 14, 10, pnt=(x - 9, y - 7, 7)))
        for fin in range(3):
            _part(parts, f"GPU_Heatsink_{i+1:02d}_{fin+1:02d}", "GPU-LLM",
                  cq.Solid.makeBox(2.2, 10, 7, pnt=(x - 6 + 4.9*fin, y - 5, 17)))
        _part(parts, f"Kraken_GPU_Link_{i+1:02d}", "KRAKEN-CONDUITS",
              _tube(1.1, (x, y, 19), _xy(12, a, 34)))
    _part(parts, "Kraken_Coolant_Advisory_Ring", "KRAKEN-CONDUITS",
          cq.Solid.makeTorus(35, 1.3, pnt=(0, 0, 23)))

    # Core ontology graph; each node linked to the core and one source node.
    for i in range(8):
        a = i * math.tau / 8
        q = _xy(48, a, 38)
        _part(parts, f"Ontology_Memory_{i+1:02d}", "ONTOLOGY-MEMORY", _sphere(5, q))
        _part(parts, f"Memory_ProvenanceEdge_{i+1:02d}", "ONTOLOGY-MEMORY",
              _tube(.85, _xy(21, a, 38), _xy(42.5, a, 38)))
        p = _xy(82, a + .085, 34)
        _part(parts, f"Patent_Publication_{i+1:02d}", "PATENT-NETWORK", _sphere(4.8, p))
        _part(parts, f"Patent_SourceEdge_{i+1:02d}", "PATENT-NETWORK",
              _tube(.7, _xy(53.5, a, 38), _xy(76.5, a + .085, 34.4)))

    # Illustration of a curated cell-reference atlas; these are NOT living cells.
    for i in range(6):
        a = (i + .5) * math.tau / 6
        center = _xy(67, a, 61)
        _part(parts, f"SymbolicCell_Membrane_{i+1:02d}", "CELL-ATLAS", _sphere(5.2, center))
        _part(parts, f"SymbolicCell_Nucleus_{i+1:02d}", "CELL-ATLAS",
              _sphere(2.15, (center[0] + 2.5, center[1], center[2] + 2.4)))
        _part(parts, f"Cell_ReferenceStem_{i+1:02d}", "CELL-ATLAS",
              _tube(.6, _xy(67, a, 5), _xy(67, a, 55)))

    # Research halo does not represent a sensor, reading thoughts, or stimulation.
    _part(parts, "Research_ConsentHalo", "NEURAL-RESEARCH",
          cq.Solid.makeTorus(26, 1.5, pnt=(0, 0, 69)))
    for i in range(6):
        a = i * math.tau / 6
        _part(parts, f"Research_InterfaceNode_{i+1:02d}", "NEURAL-RESEARCH",
              _sphere(2.7, _xy(26, a, 69)))
        _part(parts, f"Research_ReadOnlyPath_{i+1:02d}", "NEURAL-RESEARCH",
              _tube(.65, _xy(12, a, 49), _xy(26, a, 68)))

    # Perimeter rings + 8 vertical shield posts, all deliberately inert.
    for i, (radius, z, thickness) in enumerate([(60, 48, 1.0), (75, 52, 1.3), (93, 54, 1.8)]):
        _part(parts, f"ZYRA_GovernanceRing_{i+1:02d}", "ZYRA-SHIELD",
              cq.Solid.makeTorus(radius, thickness, pnt=(0, 0, z)))
    for i in range(8):
        a = i * math.tau / 8
        _part(parts, f"ZYRA_ShieldSupport_{i+1:02d}", "ZYRA-SHIELD", _post(.95, 46, _xy(93, a, 6)))
    return parts


def _mesh_part(part: CADPart, tolerance: float) -> trimesh.Trimesh:
    vectors, faces = part.shape.tessellate(tolerance, angularTolerance=0.25)
    mesh = trimesh.Trimesh(vertices=np.array([[v.x, v.y, v.z] for v in vectors]),
                           faces=np.array(faces, dtype=np.int64), process=False)
    mesh.visual.vertex_colors = np.array((*part.rgb, 255), dtype=np.uint8)
    return mesh


def export_model(output_dir: str | Path, tolerance: float = 0.7) -> dict[str, str]:
    """Export genuine CAD BRep STEP, layered 3DFACE DXF, STL, GLB + metadata."""
    if not 0.25 <= tolerance <= 5:
        raise ValueError("tolerance must be between 0.25 and 5 mm")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = "GPT-DOUG-PINEAL-3D"
    outputs = {key: str(out / f"{name}.{ext}") for key, ext in (
        ("step", "step"), ("dxf", "dxf"), ("stl", "stl"), ("glb", "glb"),
        ("manifest", "json"))}
    parts = build_model()

    assembly = cq.Assembly(name="GPT_DOUG_PINEAL_ARCHITECTURE")
    scene = trimesh.Scene()
    dxf = ezdxf.new("R2013")
    space = dxf.modelspace()
    for layer, (rgb, _) in LAYERS.items():
        dxf.layers.add(name=layer, dxfattribs={"color": 7, "true_color": ezdxf.rgb2int(rgb)})

    for part in parts:
        assembly.add(part.shape, name=part.name, color=cq.Color(*(v / 255 for v in part.rgb)))
        mesh = _mesh_part(part, tolerance)
        scene.add_geometry(mesh, geom_name=part.name, node_name=part.name)
        for face in mesh.faces:
            points = [mesh.vertices[int(index)].tolist() for index in face]
            space.add_3dface(points, dxfattribs={"layer": part.layer,
                                               "true_color": ezdxf.rgb2int(part.rgb)})

    # DXF text is a separate non-geometry layer for human-readable CAD annotations.
    dxf.layers.add(name="ANNOTATION", dxfattribs={"color": 7})
    space.add_text("GPT-DOUG-PINEAL | SOFTWARE ARCHITECTURE | NOT AN IMPLANT",
                   dxfattribs={"layer": "ANNOTATION", "height": 3.2,
                               "insert": (-90, -116, 2)})
    for j, (layer, (rgb, description)) in enumerate(LAYERS.items()):
        space.add_text(f"{layer} - {description}",
                       dxfattribs={"layer": "ANNOTATION", "height": 2.4,
                                   "insert": (-90, -125 - j*4.5, 2)})

    assembly.save(outputs["step"], exportType="STEP")
    dxf.saveas(outputs["dxf"])
    scene.export(outputs["glb"])
    trimesh.util.concatenate(list(scene.geometry.values())).export(outputs["stl"])
    manifest = {
        "model": "GPT-DOUG-PINEAL 3D architectural system",
        "revision": "concept-001",
        "status": "conceptual_nonbiological_software_architecture",
        "units": "mm", "scale": "illustrative_only_not_manufacturing_dimensions",
        "hardware_verified": False, "live_external_feeds": False,
        "physical_neural_interface": False, "living_cell_creation": False,
        "patent_consent_required": True,
        "file_roles": {
            "STEP": "Precise named solid BReps (use FreeCAD/Fusion or a STEP-supporting CAD importer)",
            "DXF": "AutoCAD editable layered 3D triangulated faces (3DFACE entities)",
            "GLB": "Browser/3D viewer scene with editable mesh objects",
            "STL": "Single mesh view/3D printing demonstration; parts not unioned",
        },
        "layers": {layer: {"rgb": rgb, "description": description,
                           "parts": sum(p.layer == layer for p in parts)}
                   for layer, (rgb, description) in LAYERS.items()},
        "component_count": len(parts),
        "disclaimer": "Architectural metaphor only. No human brain reads/writes, biological actuation, hardware system verification, military integration or patent-data entitlement is implied.",
    }
    Path(outputs["manifest"]).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return outputs


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Build GPT-Doug-Pineal conceptual 3D CAD model")
    p.add_argument("--output", default="build")
    p.add_argument("--tolerance", type=float, default=0.7)
    opts = p.parse_args()
    result = export_model(opts.output, opts.tolerance)
    print(json.dumps(result, indent=2))
