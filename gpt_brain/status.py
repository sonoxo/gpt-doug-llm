from __future__ import annotations

import json
import os
from dataclasses import asdict

from .kernel import BrainConfig
from .memory import BrainMemory
from .ontology import OntologyIndex
from .router import AGENTS


def _provider_status() -> dict:
    try:
        from agents import llm_backend

        state = dict(llm_backend.health())
    except Exception as exc:
        return {
            "provider": "unavailable",
            "configured": False,
            "model_available": False,
            "message": f"provider health check failed: {type(exc).__name__}",
        }
    state.setdefault("configured", False)
    state.setdefault("model_available", bool(state.get("configured")))
    return state


def build_status() -> dict:
    memory = BrainMemory()
    ontology = OntologyIndex()
    ontology_data = ontology.load()
    provider = _provider_status()
    memory_parent = memory.path.parent
    core_ready = bool(ontology_data) and memory_parent.exists() and os.access(
        memory_parent, os.W_OK
    )
    model_ready = bool(provider.get("configured") and provider.get("model_available"))

    return {
        "system": "GPT-DOUG-BRAIN",
        "mode": "MATRIX_COMMAND_CENTER",
        "readiness": {
            "core_ready": core_ready,
            "model_ready": model_ready,
            "ready_for_model_tasks": core_ready and model_ready,
        },
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
        "provider": provider,
        "memory": {
            "path": str(memory.path),
            "parent_writable": memory_parent.exists() and os.access(memory_parent, os.W_OK),
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
            "doctor": "scripts/doug-max brain-doctor",
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
