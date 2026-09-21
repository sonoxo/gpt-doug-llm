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


def test_live_visualizer_is_single_process_foreground_contract():
    root = Path(__file__).resolve().parent.parent
    live = (root / "tools" / "gptdoug_lightforce_live.py").read_text(encoding="utf-8")
    launcher = (root / "scripts" / "gpt-doug-lightforce").read_text(encoding="utf-8")

    assert "SINGLE FOREGROUND PROCESS" in live
    assert "q/Esc=RETURN CONTROL" in live
    assert "Ctrl+C=KILL SWITCH" in live
    assert "subprocess.Popen(" not in live
    assert "multiprocessing" not in live
    assert 'live|takeover|show)' in launcher
    assert 'write_state true "LIVE"' in launcher


def test_live_visualizer_plain_frames_exit_cleanly():
    root = Path(__file__).resolve().parent.parent
    live = root / "tools" / "gptdoug_lightforce_live.py"
    proc = subprocess.run(
        ["python3", str(live), "--plain", "--frames", "2", "--fps", "30"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    assert "LIGHTFORCE LIVE" in proc.stdout
    assert "999 logical swarms" in proc.stdout


def test_live_visualizer_defaults_to_100_visible_hives():
    root = Path(__file__).resolve().parent.parent
    live = (root / "tools" / "gptdoug_lightforce_live.py").read_text(encoding="utf-8")

    assert 'default=100' in live
    assert 'visible_hives={visible}/{len(cells)}' in live
    assert 'grid_cols = min(5, max(2, inner // 28))' in live
    assert 'args.cells = max(4, min(args.cells, 200))' in live


def test_live_visualizer_stability_defaults():
    root = Path(__file__).resolve().parent.parent
    live = (root / "tools" / "gptdoug_lightforce_live.py").read_text(encoding="utf-8")

    assert 'default=6.0' in live
    assert 'self.progress += (target - self.progress) * 0.10' in live
    assert 'slot = int(t // 4.0)' in live
    assert 'next_event = 24' in live
    assert 'DOUG <-> CHAOS <-> HIVE' in live
    assert 'GPT-DOUG // GPT-CHAOS // SWARM LIGHT FORCE // DARK FALL' in live
    assert '✨ GPT-DOUG' not in live
    assert '🐝 {swarms}' not in live


def test_gpt_swarm_command_is_real_wrapper():
    root = Path(__file__).resolve().parent.parent
    wrapper = (root / "scripts" / "gpt-swarm").read_text(encoding="utf-8")
    installer = (root / "scripts" / "install-lightforce").read_text(encoding="utf-8")

    assert 'exec "$LIGHTFORCE" live' in wrapper
    assert 'gpt-swarm [live|on|pulse|status|off|help]' in wrapper
    assert 'SWARM_TARGET="$BIN_DIR/gpt-swarm"' in installer
    assert 'fetch "$RAW_BASE/scripts/gpt-swarm" "$SWARM_TARGET"' in installer
    assert 'chmod 755 "$TARGET" "$SWARM_TARGET" "$LIVE_TARGET"' in installer


def test_gpt_swarm_help_exits_cleanly():
    root = Path(__file__).resolve().parent.parent
    wrapper = root / "scripts" / "gpt-swarm"
    proc = subprocess.run(
        ["bash", str(wrapper), "--help"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "Launch stable 100-HIVE live terminal swarm" in proc.stdout
