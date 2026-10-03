from pathlib import Path


def test_fall_terminal_installer_hardwires_zshenv_not_zshrc():
    root = Path(__file__).resolve().parent.parent
    script = (root / "scripts" / "install-fall-terminal").read_text(encoding="utf-8")

    assert 'ZSHENV="$HOME/.zshenv"' in script
    assert "# >>> GPTDOUG FALL PERMA >>>" in script
    assert "# <<< GPTDOUG FALL PERMA <<<" in script
    assert 'export GPTDOUG_FALL_MODE="auto"' in script
    assert 'source "$HOME/.config/gptdoug/fall-terminal.zsh"' in script
    assert "zsh -n" in script
    assert ".zshrc" not in script
