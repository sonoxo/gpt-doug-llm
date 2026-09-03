from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OntologyObject:
    object_type: str
    object_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class OntologyLink:
    source_type: str
    source_id: str
    relation: str
    target_type: str
    target_id: str
    created_at: str = field(default_factory=_now)


class OntologyGraph:
    """Small durable ontology for Wakeup3lm runtime state.

    It mirrors Palantir-style object/link/action thinking without claiming a
    Palantir deployment. All agent-visible operational state is represented as
    typed objects and links before tools act on it.
    """

    CORE_TYPES = {
        "Workspace",
        "Project",
        "File",
        "Model",
        "AgentRun",
        "AgentDecision",
        "ToolCall",
        "Process",
        "Build",
        "Preview",
        "Checkpoint",
        "Deployment",
        "PolicyDecision",
    }

    def __init__(self, persistence_path: str | Path | None = None) -> None:
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.objects: dict[tuple[str, str], OntologyObject] = {}
        self.links: list[OntologyLink] = []
        if self.persistence_path and self.persistence_path.exists():
            self._load()

    def upsert(self, object_type: str, object_id: str, **properties: Any) -> OntologyObject:
        if object_type not in self.CORE_TYPES:
            raise ValueError(f"Unsupported ontology object type: {object_type}")
        key = (object_type, object_id)
        current = self.objects.get(key)
        if current is None:
            current = OntologyObject(object_type=object_type, object_id=object_id, properties=dict(properties))
            self.objects[key] = current
        else:
            current.properties.update(properties)
            current.updated_at = _now()
        self._persist()
        return current

    def get(self, object_type: str, object_id: str) -> OntologyObject | None:
        return self.objects.get((object_type, object_id))

    def query(self, object_type: str, **matches: Any) -> list[OntologyObject]:
        results = [obj for (kind, _), obj in self.objects.items() if kind == object_type]
        for key, value in matches.items():
            results = [obj for obj in results if obj.properties.get(key) == value]
        return results

    def link(
        self,
        source_type: str,
        source_id: str,
        relation: str,
        target_type: str,
        target_id: str,
    ) -> OntologyLink:
        if self.get(source_type, source_id) is None:
            raise KeyError(f"Missing source object {source_type}:{source_id}")
        if self.get(target_type, target_id) is None:
            raise KeyError(f"Missing target object {target_type}:{target_id}")
        link = OntologyLink(source_type, source_id, relation, target_type, target_id)
        self.links.append(link)
        self._persist()
        return link

    def snapshot(self) -> dict[str, Any]:
        return {
            "objects": [asdict(obj) for obj in self.objects.values()],
            "links": [asdict(link) for link in self.links],
        }

    def _persist(self) -> None:
        if not self.persistence_path:
            return
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self.persistence_path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def _load(self) -> None:
        payload = json.loads(self.persistence_path.read_text(encoding="utf-8"))
        for raw in payload.get("objects", []):
            obj = OntologyObject(**raw)
            self.objects[(obj.object_type, obj.object_id)] = obj
        self.links = [OntologyLink(**raw) for raw in payload.get("links", [])]
