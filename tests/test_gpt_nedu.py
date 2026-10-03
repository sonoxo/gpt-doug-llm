"""Data boundaries and actual launcher behavior for novice education."""
import json
import subprocess
from pathlib import Path

import pytest

from gpt_nedu.cli import database_demo

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ["Ada", "O'Connor", "Robert'); DROP TABLE students;--", '<script>alert(1)</script>', '李', ''])
def test_names_remain_data(name):
    result = database_demo(name)
    assert result['students'] == ['Ada', name]
    assert result['table_intact'] is True
    assert database_demo('Next learner')['students'] == ['Ada', 'Next learner']


def test_launcher_from_other_directory(tmp_path):
    result = subprocess.run(['bash', str(ROOT / 'scripts/doug-max'), 'nedu', 'demo'], cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'parameter binding' in result.stdout
    assert '"table_intact": true' in result.stdout


def test_menu_returns_without_model(tmp_path):
    result = subprocess.run(['bash', str(ROOT / 'scripts/doug-max'), 'nedu'], input='q\n', cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert '1 Learn' in result.stdout


def test_ecosystem_route_has_browser_entry():
    registry = json.loads((ROOT / 'ecosystem/registry.v4.json').read_text())
    assert registry['domain_routing']['novice_education'] == 'gpt-nedu'
    divisions = [d for d in registry['internal_divisions'] if d['id'] == 'gpt-nedu']
    assert len(divisions) == 1
    assert (ROOT / divisions[0]['path'] / 'cli.py').is_file()
    resources = json.loads((ROOT / 'docs/resources.json').read_text())
    pages = [p for p in resources['items'] if p['id'] == 'gpt-nedu']
    assert len(pages) == 1
    assert (ROOT / 'docs' / pages[0]['url'] / 'index.html').is_file()


def test_max_shell_returns_to_idle(monkeypatch):
    from gpt_doug_max import MaxShell
    shell = object.__new__(MaxShell)
    states = []
    monkeypatch.setattr(shell, 'set_state', lambda state, detail: states.append(state))
    monkeypatch.setattr('builtins.input', lambda prompt: 'q')
    assert shell.handle_command('/nedu') is True
    assert states == ['LEARN', 'IDLE']
