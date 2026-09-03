import json

import pytest
from va3lm.agent_runtime import (
    AgentDecisionError,
    _verification_summary,
    execute_decision,
    parse_decision,
    run_coding_agent,
)
from va3lm.workspace import WorkspaceError, WorkspaceRuntime


def test_workspace_blocks_escape_and_sensitive_files(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    with pytest.raises(WorkspaceError):
        runtime.read_file("../outside.txt")
    with pytest.raises(WorkspaceError):
        runtime.write_file(".env", "SECRET=x", approved=True)
    with pytest.raises(WorkspaceError):
        runtime.write_file(".git/config", "x", approved=True)


def test_workspace_write_requires_approval_and_supports_restore(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    target = tmp_path / "app.py"
    target.write_text("print('old')\n", encoding="utf-8")

    with pytest.raises(WorkspaceError):
        runtime.write_file("app.py", "print('new')\n", approved=False)

    result = runtime.write_file("app.py", "print('new')\n", approved=True)
    assert result["written"] is True
    assert result["backupId"]
    assert target.read_text(encoding="utf-8") == "print('new')\n"

    restored = runtime.restore_backup(result["backupId"], approved=True)
    assert restored["restored"] is True
    assert target.read_text(encoding="utf-8") == "print('old')\n"


def test_workspace_command_allowlist_and_evidence(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    with pytest.raises(WorkspaceError):
        runtime.run_command("python -c 'print(1)'", approved=False)
    with pytest.raises(WorkspaceError):
        runtime.run_command("bash -lc 'echo nope'", approved=True)

    result = runtime.run_command("python -c 'print(123)'", approved=True)
    assert result["exitCode"] == 0
    assert result["timedOut"] is False
    assert "123" in result["stdout"]
    assert runtime.status()["commandFilesystemSandboxed"] is False


def test_git_publish_style_mutations_are_blocked(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    with pytest.raises(WorkspaceError):
        runtime.run_command("git push origin main", approved=True)
    with pytest.raises(WorkspaceError):
        runtime.run_command("npm publish", approved=True)


def test_parse_decision_accepts_fenced_json_and_rejects_unknown_action():
    decision = parse_decision(
        """```json
        {"summary":"inspect","done":false,"actions":[{"type":"inspect_project","arguments":{}}]}
        ```"""
    )
    assert decision.summary == "inspect"
    assert decision.actions[0].kind == "inspect_project"

    with pytest.raises(AgentDecisionError):
        parse_decision(
            json.dumps(
                {
                    "summary": "x",
                    "done": False,
                    "actions": [{"type": "shell", "arguments": {}}],
                }
            )
        )


def test_execute_decision_stops_at_mutation_approval_gate(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    decision = parse_decision(
        json.dumps(
            {
                "summary": "write",
                "done": False,
                "actions": [
                    {"type": "inspect_project", "arguments": {}},
                    {"type": "write_file", "arguments": {"path": "x.txt", "content": "hello"}},
                ],
            }
        )
    )
    result = execute_decision(decision, runtime, approved=False)
    assert result["state"] == "BLOCKED_PENDING_APPROVAL"
    assert result["evidence"][0]["ok"] is True
    assert result["evidence"][1]["state"] == "BLOCKED_PENDING_APPROVAL"
    assert not (tmp_path / "x.txt").exists()


def test_nonzero_command_is_failed_evidence(tmp_path):
    runtime = WorkspaceRuntime(tmp_path)
    decision = parse_decision(
        json.dumps(
            {
                "summary": "validate",
                "done": True,
                "actions": [
                    {
                        "type": "run_command",
                        "arguments": {"command": "python -c 'raise SystemExit(3)'"},
                    }
                ],
            }
        )
    )
    result = execute_decision(decision, runtime, approved=True)
    assert result["state"] == "FAILED"
    assert result["evidence"][0]["ok"] is False
    assert result["evidence"][0]["result"]["exitCode"] == 3


def test_verification_does_not_call_arbitrary_success_a_test():
    arbitrary = [
        {
            "type": "run_command",
            "ok": True,
            "result": {"command": ["python", "-c", "print(1)"], "exitCode": 0, "timedOut": False},
        }
    ]
    summary = _verification_summary(arbitrary)
    assert summary["successfulCommands"] == 1
    assert summary["successfulValidationCommands"] == 0
    assert summary["testsProven"] is False

    pytest_evidence = [
        {
            "type": "run_command",
            "ok": True,
            "result": {"command": ["pytest", "-q"], "exitCode": 0, "timedOut": False},
        }
    ]
    summary = _verification_summary(pytest_evidence)
    assert summary["testsProven"] is True
    assert summary["validationCategories"] == ["test"]


def test_coding_agent_without_model_is_truthful_hold(monkeypatch, tmp_path):
    monkeypatch.delenv("VA3LM_MODEL_URL", raising=False)
    result = run_coding_agent("build a page", workspace=str(tmp_path), approved=True)
    assert result["state"] == "MODEL_NOT_CONFIGURED"
    assert result["executed"] is False
    assert "No model decision" in result["truth"]
    assert result["plan"]["mutationGate"] == "HUMAN_APPROVAL_REQUIRED"
