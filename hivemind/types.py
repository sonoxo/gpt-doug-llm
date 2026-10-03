from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Stage(str, Enum):
    DEFINE = "define"
    COLLECT = "collect"
    PARSE = "parse"
    RETRIEVE = "retrieve"
    REMEMBER = "remember"
    COMPRESS = "compress"
    EXECUTE = "execute"
    WATCH = "watch"
    SHIP = "ship"


@dataclass(frozen=True)
class Integration:
    slug: str
    stage: Stage
    repository: str
    purpose: str
    probe_kind: str
    probe_value: str
    required: bool = False
    notes: str = ""


@dataclass
class Capability:
    integration: Integration
    available: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.integration.slug,
            "stage": self.integration.stage.value,
            "repository": self.integration.repository,
            "purpose": self.integration.purpose,
            "required": self.integration.required,
            "available": self.available,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class WorkItem:
    id: str
    stage: Stage
    objective: str
    preferred_integrations: tuple[str, ...]
    depends_on: tuple[str, ...] = ()
    parallel_group: str | None = None


@dataclass
class RunPlan:
    job: str
    items: list[WorkItem]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job,
            "items": [
                {
                    "id": item.id,
                    "stage": item.stage.value,
                    "objective": item.objective,
                    "preferred_integrations": list(item.preferred_integrations),
                    "depends_on": list(item.depends_on),
                    "parallel_group": item.parallel_group,
                }
                for item in self.items
            ],
            "metadata": self.metadata,
        }


@dataclass
class StageResult:
    item_id: str
    stage: Stage
    status: str
    integration: str | None
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stage"] = self.stage.value
        return data
