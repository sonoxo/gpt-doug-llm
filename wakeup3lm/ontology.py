from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

KERNEL_VERSION = "3.0.0"
CONTROL_PLANE = "THE_BLACK_HOUSE_V1"
CANONICAL_RELATIONSHIPS = {
    "EXECUTES",
    "USES",
    "PRODUCES",
    "DERIVED_FROM",
    "AUTHORIZES",
    "GOVERNS",
    "DEPLOYED_TO",
    "IMPLEMENTS",
    "RUNS_ON",
    "ROUTES_TO",
    "AUDITS",
    "EVIDENCES",
}


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
    """Durable Wakeup3lm state bound to the Black House kernel.

    Local IDE object types remain available for high-resolution execution state,
    while the canonical Black House object vocabulary is accepted directly.
    The graph mirrors object/link/action thinking without claiming a live
    external ontology deployment.
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
        "Mission",
        "Agent",
        "User",
        "Repository",
        "Service",
        "Tool",
        "Resource",
        "Evidence",
        "Source",
        "Decision",
        "Approval",
        "Action",
        "Incident",
        "Policy",
        "CredentialReference",
        "Artifact",
        "IntelligenceBrief",
    }

    def __init__(self, persistence_path: str | Path | None = None) -> None:
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.objects: dict[tuple[str, str], OntologyObject] = {}
        self.links: list[OntologyLink] = []
        if self.persistence_path and self.persistence_path.exists():
            self._load()

    @property
    def kernel(self) -> dict[str, Any]:
        return {
            "version": KERNEL_VERSION,
            "controlPlane": CONTROL_PLANE,
            "authority": "sonoxo/gpt-doug-llm/the-black-house",
            "relationshipTypes": sorted(CANONICAL_RELATIONSHIPS),
            "failClosed": True,
        }

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

    def canonical_link(
        self,
        source_type: str,
        source_id: str,
        relation: str,
        target_type: str,
        target_id: str,
    ) -> OntologyLink:
        if relation not in CANONICAL_RELATIONSHIPS:
            raise ValueError(f"Unsupported Black House relationship: {relation}")
        return self.link(source_type, source_id, relation, target_type, target_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "kernel": self.kernel,
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
