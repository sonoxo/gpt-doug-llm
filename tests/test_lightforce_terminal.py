import json
import os
import subprocess
from pathlib import Path


def test_lightforce_writes_bounded_logical_state(tmp_path):
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "gpt-doug-lightforce"
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["GPTDOUG_LIGHTFORCE_NO_ANIM"] = "1"

    proc = subprocess.run(
        ["bash", str(script), "on"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    state_file = tmp_path / ".gpt-doug" / "lightforce-state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["active"] is True
    assert state["logical_swarms"] == 999
    assert state["logical_hives"] == 999
    assert state["hidden_processes_spawned"] == 0
    assert state["human_override"] is True
    assert state["peer_mode"] == "DOUG_EQUALS_CHAOS"


def test_lightforce_off_is_non_background(tmp_path):
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "gpt-doug-lightforce"
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["GPTDOUG_LIGHTFORCE_NO_ANIM"] = "1"

    subprocess.run(["bash", str(script), "on"], env=env, check=True)
    subprocess.run(["bash", str(script), "off"], env=env, check=True)

    state = json.loads(
        (tmp_path / ".gpt-doug" / "lightforce-state.json").read_text(encoding="utf-8")
    )
    assert state["active"] is False
    assert state["hidden_processes_spawned"] == 0


def test_max_shell_exposes_lightforce_command():
    root = Path(__file__).resolve().parent.parent
    text = (root / "gpt_doug_max.py").read_text(encoding="utf-8")
    assert "/lightforce" in text
    assert "cmd_lightforce" in text
