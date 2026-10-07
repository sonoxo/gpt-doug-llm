import os
import shutil
import stat
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gpt-doug-local"


def _write_exec(path: Path, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, root / "scripts" / "gpt-doug-local")
    (root / "scripts" / "gpt-doug-local").chmod(0o755)
    return root


def test_launcher_prefers_project_venv(tmp_path: Path):
    root = _repo(tmp_path)
    _write_exec(root / ".venv" / "bin" / "python", "#!/bin/sh\necho VENV:$*\n")
    result = subprocess.run(
        [str(root / "scripts" / "gpt-doug-local"), "godseye", "status"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "VENV:-m gpt_brain.cli godseye status" in result.stdout


def test_launcher_falls_back_to_python3_without_pip(tmp_path: Path):
    root = _repo(tmp_path)
    fakebin = tmp_path / "bin"
    _write_exec(fakebin / "python3", "#!/bin/sh\necho PY3:$*\n")
    env = {**os.environ, "PATH": str(fakebin)}
    result = subprocess.run(
        [str(root / "scripts" / "gpt-doug-local"), "planetary", "status"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert "PY3:-m gpt_brain.cli planetary status" in result.stdout
    assert "pip install" not in SCRIPT.read_text(encoding="utf-8")


def test_launcher_returns_127_without_python(tmp_path: Path):
    root = _repo(tmp_path)
    env = {**os.environ, "PATH": str(tmp_path / "empty")}
    result = subprocess.run(
        [str(root / "scripts" / "gpt-doug-local"), "status"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 127
    assert "python3 is required" in result.stderr
