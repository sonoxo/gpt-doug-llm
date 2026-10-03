from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional

from .models import OntologyObject


class OntologyStore:
    """Small in-memory ontology store with JSON export.

    This is intentionally simple so it can later be replaced by a Palantir
    Ontology adapter without changing the domain model.
    """

    def __init__(self) -> None:
        self._objects: Dict[str, OntologyObject] = {}

    def add(self, obj: OntologyObject) -> OntologyObject:
        self._objects[obj.id] = obj
        return obj

    def get(self, object_id: str) -> Optional[OntologyObject]:
        return self._objects.get(object_id)

    def all(self) -> Iterable[OntologyObject]:
        return self._objects.values()

    def export_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [obj.to_dict() for obj in self._objects.values()]
        target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return target
