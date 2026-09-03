from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.authorized_web_content_discovery import (
    DiscoveryAuthorizationError,
    DiscoveryRequest,
    DiscoveryRuntimeError,
    build_feroxbuster_command,
    execute_discovery,
    skill_manifest,
    validate_scope,
)


def request(**overrides):
    values = {
        "target": "https://example.test",
        "authorized": True,
        "allowed_hosts": ("example.test",),
        "depth": 2,
        "rate_limit": 20,
        "threads": 20,
    }
    values.update(overrides)
    return DiscoveryRequest(**values)


def test_rejects_unauthorized_execution():
    with pytest.raises(DiscoveryAuthorizationError):
        validate_scope(request(authorized=False))


def test_rejects_target_outside_scope():
    with pytest.raises(DiscoveryAuthorizationError):
        validate_scope(request(target="https://outside.test"))


def test_builds_bounded_feroxbuster_command(tmp_path):
    cmd = build_feroxbuster_command(request(), str(tmp_path / "results.jsonl"))
    assert cmd[0] == "feroxbuster"
    assert "--depth" in cmd and "2" in cmd
    assert "--rate-limit" in cmd and "20" in cmd
    assert "--threads" in cmd and "20" in cmd
    assert "--json" in cmd


def test_runtime_refuses_when_tool_missing(monkeypatch):
    monkeypatch.setattr("agents.authorized_web_content_discovery.shutil.which", lambda _: None)
    with pytest.raises(DiscoveryRuntimeError):
        execute_discovery(request())


def test_runtime_parses_structured_findings(monkeypatch, tmp_path):
    monkeypatch.setattr("agents.authorized_web_content_discovery.shutil.which", lambda _: "/usr/bin/feroxbuster")

    def fake_run(cmd, cwd, text, capture_output, timeout, check):
        output = Path(cmd[cmd.index("--output") + 1])
        output.write_text(json.dumps({"url": "https://example.test/admin", "status": 200}) + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("agents.authorized_web_content_discovery.subprocess.run", fake_run)
    result = execute_discovery(request(), tmp_path)
    assert result.executed is True
    assert result.returncode == 0
    assert result.findings[0]["status"] == 200


def test_skill_manifest_marks_models_and_scope_policy():
    manifest = skill_manifest()
    assert "gpt-doug-astra-llm" in manifest["learnedBy"]
    assert "gpt-doug-llm" in manifest["learnedBy"]
    assert manifest["executionPolicy"] == "FAIL_CLOSED_AUTHORIZED_SCOPE_ONLY"
