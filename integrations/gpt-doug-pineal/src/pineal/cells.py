"""Curated educational metadata for human cells; never a wet-lab recipe.

A cell is a molecular biological system, not a software or binary object.
The symbolic timeline is a diagrammatic metaphor, not a mechanistic simulator.
"""
from __future__ import annotations

from copy import deepcopy

_CELL_ATLAS: tuple[dict[str, str], ...] = (
    {"id": "neuron", "function": "electrical and chemical signaling in nervous tissue", "lineage": "ectoderm-derived neural lineage", "caution": "many mature neurons are post-mitotic"},
    {"id": "cardiomyocyte", "function": "contraction of cardiac muscle", "lineage": "mesoderm-derived cardiac lineage", "caution": "adult cardiomyocyte regeneration is limited"},
    {"id": "hepatocyte", "function": "liver metabolism and synthesis", "lineage": "endoderm-derived hepatic lineage", "caution": "liver regeneration is regulated and tissue-dependent"},
    {"id": "t_lymphocyte", "function": "adaptive immune surveillance and response", "lineage": "hematopoietic lymphoid lineage", "caution": "immune signaling is contextual and cannot be predicted here"},
    {"id": "hematopoietic_stem_cell", "function": "maintains blood and immune cell lineages", "lineage": "hematopoietic stem/progenitor hierarchy", "caution": "self-renewal and lineage commitment depend on tissue niches"},
    {"id": "fibroblast", "function": "extracellular matrix synthesis and tissue support", "lineage": "predominantly mesenchymal lineages", "caution": "many fibroblast phenotypes are tissue-specific"},
    {"id": "keratinocyte", "function": "epidermal barrier formation", "lineage": "surface ectoderm epithelial lineage", "caution": "proliferative capacity depends on differentiation state"},
    {"id": "erythrocyte", "function": "oxygen and carbon dioxide transport", "lineage": "erythroid lineage", "caution": "mature human red blood cells lack a nucleus"},
    {"id": "intestinal_stem_cell", "function": "epithelial renewal in intestine", "lineage": "endoderm-derived intestinal epithelial lineage", "caution": "cell fate is regulated by local signals"},
    {"id": "embryonic_stem_cell", "function": "pluripotent cell model in developmental research", "lineage": "early embryonic pluripotent lineage", "caution": "human embryo research is ethically and legally regulated"},
)

_LIMITATIONS = (
    "Educational symbolic states only: no real cells are produced, grown, or edited. "
    "Human DNA is chemical information and is not literally binary computer code. "
    "Human parthenogenesis is not an established path to viable human reproduction; "
    "parent-of-origin genomic imprinting is a major developmental barrier."
)


def list_cells() -> list[dict[str, str]]:
    """Return safe curated reference data for educational ontology links."""
    return [{**deepcopy(cell), "species": "Homo sapiens", "status": "educational_metadata"}
            for cell in _CELL_ATLAS]


def simulate(cell_id: str, steps: int = 6) -> dict:
    """Return a deterministic illustrative cycle, not biological predictions."""
    names = {cell["id"] for cell in _CELL_ATLAS}
    if cell_id not in names:
        raise ValueError("cell must be a listed educational human cell type")
    if type(steps) is not int or not 1 <= steps <= 50:
        raise ValueError("steps must be an integer from 1 to 50")
    labels = ("baseline", "signaling", "homeostasis", "quality_checkpoint")
    timeline = [{"step": i + 1, "symbolic_state": labels[i % len(labels)],
                 "real_biological_measurement": False} for i in range(steps)]
    return {"cell": cell_id, "mode": "symbolic_educational_simulation",
            "created_living_cells": False, "timeline": timeline,
            "scientific_limitations": _LIMITATIONS}


def search_cells(query: str) -> list[dict[str, str]]:
    """Find curated cell reference data; no biological inference from patents."""
    if not isinstance(query, str) or len(query) > 256:
        raise ValueError("cell query must be text up to 256 characters")
    term = query.strip().lower()
    if not term:
        return []
    return [row for row in list_cells()
            if any(term in str(row[field]).lower() for field in ("id", "function", "lineage"))]
