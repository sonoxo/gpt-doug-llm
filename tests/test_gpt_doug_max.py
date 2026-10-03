import json

import gpt_doug_max as gm


def test_shell_read_only_classification():
    assert gm.shell_is_read_only("git status")
    assert gm.shell_is_read_only("git diff --stat")
    assert gm.shell_is_read_only("ls -la")
    assert gm.shell_is_read_only("ollama list")
    assert not gm.shell_is_read_only('python3 -c "open(\'/tmp/x\', \'w\').write(\'x\')"')
    assert not gm.shell_is_read_only("git commit -am test")
    assert not gm.shell_is_read_only("rm -rf build")
    assert not gm.shell_is_read_only("ls | tee /tmp/out")
    assert not gm.shell_is_read_only("curl -X POST https://example.com")


def test_arm_gate_expires(monkeypatch):
    gate = gm.ArmGate()
    now = [1000.0]
    monkeypatch.setattr(gm.time, "time", lambda: now[0])
    gate.arm(30)
    assert gate.active()
    assert gate.remaining() == 30
    now[0] = 1031.0
    assert not gate.active()
    assert gate.remaining() == 0


def test_state_bus_atomic_write(tmp_path):
    path = tmp_path / "state.json"
    bus = gm.StateBus(path)
    bus.set("THINK", "unit test", provider="ollama", model="gpt-xunia-brain")
    payload = json.loads(path.read_text())
    assert payload["state"] == "THINK"
    assert payload["detail"] == "unit test"
    assert payload["provider"] == "ollama"
    assert payload["model"] == "gpt-xunia-brain"
