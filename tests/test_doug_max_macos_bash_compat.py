from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "doug-max"


def test_doug_max_avoids_bash4_case_modifiers() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "${1,,}" not in text
    assert "${goal,,}" not in text
    assert "tr '[:upper:]' '[:lower:]'" in text


def test_doug_max_shell_syntax_is_valid() -> None:
    result = subprocess.run(
        ["/bin/bash", "-n", str(LAUNCHER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
