from __future__ import annotations

import doug_terminal_agent as agent


def test_finish_schema_exposes_verify_command():
    properties = agent.ACTION_SCHEMA["properties"]
    assert "verify_command" in properties
    assert properties["action"]["enum"] == ["shell", "finish"]


def test_command_fingerprint_normalizes_whitespace():
    first = agent.command_fingerprint("python   -m pytest  tests")
    second = agent.command_fingerprint("python -m pytest tests")
    assert first == second


def test_unsafe_command_is_blocked_before_execution():
    code, stdout, stderr = agent.run("sudo rm -rf /tmp/example")
    assert code == 126
    assert stdout == ""
    assert "BLOCKED unsafe command" in stderr


def test_context_compaction_preserves_objective_and_recent_evidence(monkeypatch):
    monkeypatch.setattr(agent, "MAX_CONTEXT_CHARS", 12000)
    messages = [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": "original objective"},
    ]
    for index in range(20):
        messages.append({"role": "assistant", "content": "a" * 1000})
        messages.append({"role": "user", "content": f"observation-{index}-" + "b" * 1000})

    compacted = agent.compact_messages(messages)

    assert compacted[0]["content"] == "system rules"
    assert compacted[1]["content"] == "original objective"
    assert any("CONTEXT COMPACTED" in item["content"] for item in compacted)
    assert "observation-19" in compacted[-1]["content"]
    assert len(compacted) < len(messages)
