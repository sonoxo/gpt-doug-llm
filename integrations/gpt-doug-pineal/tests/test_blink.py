import io
import json

import pytest

from pineal.blink import render_blink, run_blink
from pineal.cli import main
from pineal.store import PinealStore


def test_blink_is_visual_symbolic_and_not_a_live_cell(tmp_path):
    store = PinealStore(tmp_path / 'state.sqlite3')
    first = render_blink(store, frame=0, color=False)
    second = render_blink(store, frame=1, color=False)
    assert first != second
    for term in ('PINEAL', 'BLINK', 'CELL ATLAS', 'PATENT', 'LOCAL', 'SYMBOLIC'):
        assert term in first.upper()
    assert '0 indexed' in first.lower()
    assert 'NO HUMAN BRAIN' in first.upper()
    assert 'LIVING CELLS CREATED: NO' in first.upper()
    assert store.verify_audit()['checked'] == 0


def test_blink_is_bounded_on_non_tty_and_rejects_invalid_frames(tmp_path):
    store = PinealStore(tmp_path / 'state.sqlite3')
    out = io.StringIO()
    assert run_blink(store, watch=True, frames=2, interval=0.001, stream=out, color=False) == 0
    assert out.getvalue().count('PINEAL // BLINK') == 2
    assert '\x1b[' not in out.getvalue()
    with pytest.raises(ValueError):
        run_blink(store, frames=0, stream=out)
    with pytest.raises(ValueError):
        run_blink(store, watch=True, interval=float('nan'), frames=2, stream=out)


def test_cli_cell_atlas_patent_catalog_and_blink(tmp_path, capsys):
    home = str(tmp_path / 'state')
    assert main(['--home', home, 'cells', 'list']) == 0
    data = json.loads(capsys.readouterr().out)
    assert any(x['id'] == 'neuron' for x in data['cells'])
    assert main(['--home', home, 'cells', 'simulate', 'neuron', '--steps', '3']) == 0
    timeline = json.loads(capsys.readouterr().out)
    assert timeline['created_living_cells'] is False
    assert len(timeline['timeline']) == 3
    assert main(['--home', home, 'patents', 'sources']) == 0
    assert json.loads(capsys.readouterr().out)['connected_count'] == 0
    assert main(['--home', home, 'patents', 'stats']) == 0
    assert json.loads(capsys.readouterr().out)['total'] == 0
    assert main(['--home', home, 'blink', '--frames', '2', '--interval', '0.001', '--no-color']) == 0
    assert capsys.readouterr().out.count('PINEAL // BLINK') == 2


def test_cli_offline_patent_import_search_and_explicit_online_required(tmp_path, capsys):
    home = str(tmp_path / 'state')
    path = tmp_path / 'safe.jsonl'
    path.write_text(json.dumps({'publication_id': 'US20260313851A1', 'title': 'GPU cooling disclosed',
                                'publication_date': '2026-10-08', 'source': 'manual-uspto-reference',
                                'source_url': 'https://patents.google.com/patent/US20260313851A1/en'}) + '\n')
    assert main(['--home', home, 'patents', 'import', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['inserted'] == 1
    assert main(['--home', home, 'patents', 'search', 'GPU']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['count'] == 1
    assert main(['--home', home, 'patents', 'fetch', 'EP0084638A1']) == 2
    assert 'online' in capsys.readouterr().err.lower()


def test_existing_dashboard_includes_live_local_index_count(tmp_path):
    from pineal.dashboard import render_dashboard
    store = PinealStore(tmp_path / 'state.sqlite3')
    frame = render_dashboard(store, demo=True)
    assert 'CELL ATLAS' in frame
    assert 'PATENT INDEX' in frame
    assert '0 local' in frame
    assert 'NO THIRD-PARTY ACCESS' in frame


def test_context_search_wires_local_patent_evidence_without_asserting_validity(tmp_path, capsys):
    home = str(tmp_path / 'state')
    path = tmp_path / 'patents.jsonl'
    path.write_text(json.dumps({'publication_id':'US20260313851A1','title':'GPU cooling disclosure',
                                'publication_date':'2026-10-08','source':'research import',
                                'source_url':'https://patents.google.com/patent/US20260313851A1/en'})+'\n')
    assert main(['--home',home,'patents','import',str(path)]) == 0
    capsys.readouterr()
    assert main(['--home',home,'context','cooling']) == 0
    result=json.loads(capsys.readouterr().out)
    assert result['patent_publications'][0]['publication_id']=='US20260313851A1'
    assert 'not' in result['patent_evidence_notice'].lower()
