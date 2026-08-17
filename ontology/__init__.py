from .models import Entity, Relation, Evidence
from .store import OntologyStore
from .ingest import DocumentIngestor

__all__ = [
    "Entity",
    "Relation",
    "Evidence",
    "OntologyStore",
    "DocumentIngestor",
]

# GPT-DOUG LEGACY ONTOLOGY COMPATIBILITY
#
# Preserve the public ``from ontology import Ontology`` contract while
# keeping the current ontology package (models/store/ingest) authoritative.
import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _Path

_legacy_ontology_path = _Path(__file__).resolve().parent.parent / "ontology.py"
_legacy_ontology_spec = _importlib_util.spec_from_file_location(
    "_gpt_doug_legacy_ontology",
    _legacy_ontology_path,
)

if (
    _legacy_ontology_spec is None
    or _legacy_ontology_spec.loader is None
):
    raise ImportError(
        f"Unable to load legacy Ontology compatibility module: "
        f"{_legacy_ontology_path}"
    )

_legacy_ontology_module = _importlib_util.module_from_spec(
    _legacy_ontology_spec
)
_sys.modules[_legacy_ontology_spec.name] = _legacy_ontology_module
_legacy_ontology_spec.loader.exec_module(_legacy_ontology_module)

Ontology = _legacy_ontology_module.Ontology

if "Ontology" not in __all__:
    __all__.append("Ontology")
