import json
from pathlib import Path
import tempfile

import pytest

from wakeup3lm import Wakeup3LM
from wakeup3lm.runtime import DecisionStatus
from wakeup3lm.workspace import WorkspaceFS, WorkspaceSecurityError


def test_invalid_agent_decision_fails_closed_without_crashing():
    with tempfile.TemporaryDirectory() as tmp:
        llm = Wakeup3LM(tmp)
        result = llm.execute("not-json")
        assert result.status is DecisionStatus.FAILED
        assert "valid JSON" in result.error
        failed = llm.ontology.query("AgentDecision", status="FAILED")
        assert len(failed) == 1


def test_unknown_tool_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        llm = Wakeup3LM(tmp)
        result = llm.execute({"action": "hack_everything", "arguments": {}})
        assert result.status is DecisionStatus.FAILED
        assert "unregistered" in result.error


def test_write_read_and_ontology_audit():
    with tempfile.TemporaryDirectory() as tmp:
        llm = Wakeup3LM(tmp)
        write = llm.execute({
            "action": "write_file",
            "arguments": {"path": "src/index.html", "content": "<h1>Wakeup3lm</h1>"},
            "rationale": "create project entrypoint",
        })
        assert write.status is DecisionStatus.PASSED
        read = llm.execute({"action": "read_file", "arguments": {"path": "src/index.html"}})
        assert read.output == "<h1>Wakeup3lm</h1>"
        assert llm.ontology.query("ToolCall", status="PASSED")
        assert llm.ontology.query("AgentDecision", status="PASSED")


def test_workspace_blocks_path_escape():
    with tempfile.TemporaryDirectory() as tmp:
        fs = WorkspaceFS(tmp)
        with pytest.raises(WorkspaceSecurityError):
            fs.write_file("../outside.txt", "blocked")


def test_ontology_persists_state():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.json"
        workspace = Path(tmp) / "workspace"
        llm = Wakeup3LM(workspace, state)
        result = llm.execute({"action": "write_file", "arguments": {"path": "README.md", "content": "ok"}})
        assert result.status is DecisionStatus.PASSED
        payload = json.loads(state.read_text())
        assert any(item["object_type"] == "ToolCall" for item in payload["objects"])
        restored = Wakeup3LM(workspace, state)
        assert restored.ontology.query("ToolCall", status="PASSED")
