from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAYER_MANIFEST = ROOT / "the-black-house" / "layers" / "green-house" / "layer.manifest.json"
ONTOLOGY = ROOT / "the-green-house" / "ontology" / "green-house-ontology.json"


class GreenHouseRuntimeError(RuntimeError):
    pass


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise GreenHouseRuntimeError(f"required Green House artifact missing: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise GreenHouseRuntimeError(f"invalid Green House JSON: {path.relative_to(ROOT)}") from exc


@lru_cache(maxsize=1)
def load_green_house_runtime() -> dict:
    layer = _load_json(LAYER_MANIFEST)
    ontology = _load_json(ONTOLOGY)

    if layer.get("layerId") != "THE_GREEN_HOUSE_V1":
        raise GreenHouseRuntimeError("Green House layerId mismatch")
    if layer.get("parentControlPlane") != "THE_BLACK_HOUSE_V1":
        raise GreenHouseRuntimeError("Green House parent control plane mismatch")
    if layer.get("parentKernelVersion") != "3.0.0":
        raise GreenHouseRuntimeError("Green House parent kernel mismatch")
    if layer.get("sourceOntology") != "the-green-house/ontology/green-house-ontology.json":
        raise GreenHouseRuntimeError("Green House ontology binding mismatch")
    if ontology.get("scope") != ["eco", "bio", "pharma", "fda"]:
        raise GreenHouseRuntimeError("Green House ontology scope mismatch")
    if ontology.get("connectionState") != "NO_EXTERNAL_REGULATOR_CONNECTION_CLAIMED":
        raise GreenHouseRuntimeError("Green House regulator truth-state mismatch")

    object_types = ontology.get("objectTypes") or []
    link_types = ontology.get("linkTypes") or []
    action_types = ontology.get("actionTypes") or []
    if not object_types or not link_types or not action_types:
        raise GreenHouseRuntimeError("Green House ontology is incomplete")

    return {
        "layerId": "THE_GREEN_HOUSE_V1",
        "parentControlPlane": "THE_BLACK_HOUSE_V1",
        "kernelVersion": "3.0.0",
        "runtimeMounted": True,
        "runtimeState": "RUNTIME_MOUNTED",
        "missionProtocol": layer["routing"]["missionProtocol"],
        "domains": list(layer["domain"]),
        "ontology": {
            "name": ontology["name"],
            "version": ontology["version"],
            "objectTypeCount": len(object_types),
            "linkTypeCount": len(link_types),
            "actionTypeCount": len(action_types),
        },
        "governance": layer["governance"],
        "externalRegulatorConnection": "NOT_CLAIMED",
        "authorizationState": ontology["authorizationState"],
    }


def green_house_status() -> dict:
    return load_green_house_runtime()


def reset_green_house_runtime_for_tests() -> None:
    load_green_house_runtime.cache_clear()
