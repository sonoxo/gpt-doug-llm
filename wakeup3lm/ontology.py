from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

KERNEL_VERSION = "3.1.0"
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

    Persistence is write-coalesced inside ``batch()`` blocks. This keeps the
    fail-closed/auditable state model while avoiding a complete JSON snapshot
    rewrite for every object or relationship mutation in one logical phase.
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
        self._batch_depth = 0
        self._dirty = False
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
            "persistence": "atomic-write-coalesced",
        }

    @contextmanager
    def batch(self) -> Iterator["OntologyGraph"]:
        """Coalesce related mutations into one durable snapshot write.

        Nested batches are supported. The outermost batch flushes once even if
        an exception occurs, preserving the prior behavior that completed state
        mutations are durable rather than silently discarded.
        """
        self._batch_depth += 1
        try:
            yield self
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._dirty:
                self._persist_now()

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
        if self._batch_depth > 0:
            self._dirty = True
            return
        self._persist_now()

    def _persist_now(self) -> None:
        if not self.persistence_path:
            self._dirty = False
            return
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.snapshot(), indent=2)
        temporary = self.persistence_path.with_name(f".{self.persistence_path.name}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.persistence_path)
        self._dirty = False

    def _load(self) -> None:
        payload = json.loads(self.persistence_path.read_text(encoding="utf-8"))
        for raw in payload.get("objects", []):
            obj = OntologyObject(**raw)
            self.objects[(obj.object_type, obj.object_id)] = obj
        self.links = [OntologyLink(**raw) for raw in payload.get("links", [])]
