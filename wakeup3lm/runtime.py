from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .ontology import OntologyGraph
from .workspace import WorkspaceFS


class DecisionStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass
class AgentDecision:
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    status: DecisionStatus = DecisionStatus.PLANNED
    decision_id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def from_payload(cls, payload: str | dict[str, Any]) -> "AgentDecision":
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as error:
                raise ValueError(f"agent decision is not valid JSON: {error.msg}") from error
        if not isinstance(payload, dict):
            raise ValueError("agent decision must be a JSON object")
        action = payload.get("action")
        arguments = payload.get("arguments", {})
        rationale = payload.get("rationale", "")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("agent decision requires a non-empty action")
        if not isinstance(arguments, dict):
            raise ValueError("agent decision arguments must be an object")
        if not isinstance(rationale, str):
            raise ValueError("agent decision rationale must be a string")
        return cls(action=action.strip(), arguments=arguments, rationale=rationale)


@dataclass
class ToolResult:
    tool: str
    status: DecisionStatus
    output: Any = None
    error: str = ""


class Wakeup3LM:
    """Ontology-first IDE LLM execution kernel.

    The model proposes a structured AgentDecision. This runtime validates the
    decision, records it in the ontology, and only then dispatches a registered
    IDE tool. Invalid model output becomes a governed FAILED decision instead of
    crashing the IDE.

    Related ontology mutations are committed in bounded phases: one durable
    pre-dispatch write and one terminal-result write. This preserves audit
    visibility before tool execution while removing per-object write
    amplification.
    """

    def __init__(self, workspace_root: str | Path, state_path: str | Path | None = None) -> None:
        self.workspace = WorkspaceFS(workspace_root)
        self.ontology = OntologyGraph(state_path)
        self.tools: dict[str, Callable[..., Any]] = {
            "read_file": self.workspace.read_file,
            "write_file": self.workspace.write_file,
            "delete_file": self.workspace.delete_file,
            "list_directory": self.workspace.list_directory,
            "search_files": self.workspace.search_files,
        }
        with self.ontology.batch():
            self.ontology.upsert("Workspace", "default", root=str(self.workspace.root), runtime="Wakeup3lm")
            self.ontology.upsert("Model", "wakeup3lm", role="IDE LLM", architecture="ontology-first")
            self.ontology.link("Model", "wakeup3lm", "OPERATES_IN", "Workspace", "default")

    @property
    def tool_schema(self) -> dict[str, Any]:
        return {
            "decision_schema": {
                "action": "registered tool name",
                "arguments": "JSON object",
                "rationale": "short explanation",
            },
            "tools": sorted(self.tools),
            "statuses": [status.value for status in DecisionStatus],
        }

    def validate_decision(self, payload: str | dict[str, Any]) -> AgentDecision:
        decision = AgentDecision.from_payload(payload)
        if decision.action not in self.tools:
            raise ValueError(f"unregistered Wakeup3lm tool: {decision.action}")
        return decision

    def execute(self, payload: str | dict[str, Any]) -> ToolResult:
        try:
            decision = self.validate_decision(payload)
        except ValueError as error:
            decision_id = uuid4().hex
            self.ontology.upsert(
                "AgentDecision",
                decision_id,
                status=DecisionStatus.FAILED.value,
                error=str(error),
                raw=payload if isinstance(payload, dict) else str(payload)[:4000],
            )
            return ToolResult("decision_validation", DecisionStatus.FAILED, error=str(error))

        call_id = uuid4().hex
        with self.ontology.batch():
            self.ontology.upsert(
                "AgentDecision",
                decision.decision_id,
                action=decision.action,
                arguments=decision.arguments,
                rationale=decision.rationale,
                status=DecisionStatus.RUNNING.value,
            )
            self.ontology.link("Model", "wakeup3lm", "PROPOSED", "AgentDecision", decision.decision_id)
            self.ontology.upsert(
                "ToolCall",
                call_id,
                tool=decision.action,
                arguments=decision.arguments,
                status=DecisionStatus.RUNNING.value,
            )
            self.ontology.link("AgentDecision", decision.decision_id, "REQUESTED", "ToolCall", call_id)

        try:
            output = self.tools[decision.action](**decision.arguments)
        except Exception as error:
            with self.ontology.batch():
                self.ontology.upsert("ToolCall", call_id, status=DecisionStatus.FAILED.value, error=str(error))
                self.ontology.upsert("AgentDecision", decision.decision_id, status=DecisionStatus.FAILED.value)
            return ToolResult(decision.action, DecisionStatus.FAILED, error=str(error))

        with self.ontology.batch():
            self.ontology.upsert("ToolCall", call_id, status=DecisionStatus.PASSED.value, output=output)
            self.ontology.upsert("AgentDecision", decision.decision_id, status=DecisionStatus.PASSED.value)
        return ToolResult(decision.action, DecisionStatus.PASSED, output=output)

    def state(self) -> dict[str, Any]:
        return {
            "identity": "Wakeup3lm",
            "role": "IDE LLM",
            "architecture": "Black House / ontology-first",
            "tool_schema": self.tool_schema,
            "ontology": self.ontology.snapshot(),
        }

    def state_json(self) -> str:
        return json.dumps(self.state(), indent=2, default=str)
