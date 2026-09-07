from pathlib import Path

import pytest

from wakeup3lm.computer_agent import (
    ApprovalRequired,
    ComputerAgentError,
    ComputerToolbox,
    WorkspaceBoundaryError,
    attach_computer_tools,
    classify_shell_command,
)


def test_shell_classifier_separates_safe_approval_and_blocked():
    assert classify_shell_command("pwd") == "safe"
    assert classify_shell_command("git status") == "safe"
    assert classify_shell_command("touch hello.txt") == "approval"
    assert classify_shell_command("ls && touch nope") == "approval"
    assert classify_shell_command("rm -rf /") == "blocked"


def test_safe_shell_command_runs_without_approval(tmp_path: Path):
    toolbox = ComputerToolbox(tmp_path)
    result = toolbox.run_shell("pwd")
    assert result["returncode"] == 0
    assert result["risk"] == "safe"
    assert result["stdout"].strip() == str(tmp_path.resolve())


def test_side_effecting_shell_command_requires_approval(tmp_path: Path):
    toolbox = ComputerToolbox(tmp_path)
    with pytest.raises(ApprovalRequired):
        toolbox.run_shell("touch hello.txt")
    result = toolbox.run_shell("touch hello.txt", approve=True)
    assert result["returncode"] == 0
    assert (tmp_path / "hello.txt").exists()


def test_catastrophic_shell_command_is_blocked_even_if_approved(tmp_path: Path):
    toolbox = ComputerToolbox(tmp_path)
    with pytest.raises(ComputerAgentError):
        toolbox.run_shell("rm -rf /", approve=True)


def test_cwd_cannot_escape_workspace(tmp_path: Path):
    toolbox = ComputerToolbox(tmp_path)
    with pytest.raises(WorkspaceBoundaryError):
        toolbox.run_shell("pwd", cwd="..")


def test_browser_rejects_non_http_url_before_navigation(tmp_path: Path):
    toolbox = ComputerToolbox(tmp_path)
    with pytest.raises(ComputerAgentError):
        toolbox._validate_url("file:///etc/passwd")


def test_attach_registers_computer_tools_and_ontology(tmp_path: Path):
    class Workspace:
        root = tmp_path

    class Ontology:
        def __init__(self):
            self.objects = []
            self.links = []

        def upsert(self, *args, **kwargs):
            self.objects.append((args, kwargs))

        def link(self, *args):
            self.links.append(args)

    class Runtime:
        workspace = Workspace()
        ontology = Ontology()
        tools = {}

    runtime = Runtime()
    toolbox = attach_computer_tools(runtime)
    assert runtime.tools["run_shell"] == toolbox.run_shell
    assert "browser_open" in runtime.tools
    assert "desktop_click" in runtime.tools
    assert runtime.ontology.objects
    assert runtime.ontology.links
