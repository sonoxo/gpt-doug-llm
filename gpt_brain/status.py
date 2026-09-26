from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .kernel import BrainConfig
from .memory import BrainMemory
from .ontology import OntologyIndex
from .router import AGENTS


def build_status() -> dict:
    memory = BrainMemory()
    ontology = OntologyIndex()
    ontology_data = ontology.load()
    return {
        "system": "GPT-DOUG-BRAIN",
        "mode": "MATRIX_COMMAND_CENTER",
        "brain": {
            "kernel": "ontology-first multi-agent orchestration",
            "config": asdict(BrainConfig()),
            "specialists": {
                name: {
                    "purpose": spec.purpose,
                    "weight": spec.weight,
                }
                for name, spec in AGENTS.items()
            },
        },
        "memory": {
            "path": str(memory.path),
            "records": len(memory.records()),
            "kinds": sorted(memory.VALID_KINDS),
        },
        "ontology": {
            "path": str(ontology.path),
            "available": bool(ontology_data),
            "ontology_id": ontology_data.get("ontology_id"),
            "schema_version": ontology_data.get("schema_version"),
            "domains": sorted((ontology_data.get("domains") or {}).keys()),
        },
        "interfaces": {
            "launcher": "scripts/doug-max",
            "brain": "scripts/doug-max brain",
            "swarm": "scripts/doug-max swarm",
            "clone_ingest": "scripts/doug-max clone",
            "recall": "scripts/doug-max brain-recall",
            "matrix_status": "scripts/doug-max matrix",
        },
        "design_target": [
            "live ontology graph",
            "parallel specialist swarm",
            "evidence/provenance timeline",
            "voice/gesture-ready control surface",
            "predictive hypotheses clearly separated from facts",
        ],
    }


def main() -> int:
    print(json.dumps(build_status(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
