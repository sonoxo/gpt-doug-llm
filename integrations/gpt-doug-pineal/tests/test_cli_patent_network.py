"""CLI-to-store contracts for operator authorized patent network wiring."""
import json

import pytest

from pineal.cli import main
from pineal.store import PinealStore
from pineal.patents import validate_record


def sample(id='US20260305554A1', title='Cell research disclosure'):
    return validate_record({
        'publication_id': id, 'title': title, 'publication_date': '2026-10-08',
        'source': 'EPO Open Patent Services (OPS)',
        'source_url': f'https://patents.google.com/patent/{id}/en',
        'cpc': '', 'cell_tags': [],
    })


def test_connect_status_does_not_trigger_network_or_claim_success(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('EPO_OPS_KEY', 'configured-test-key')
    monkeypatch.setenv('EPO_OPS_SECRET', 'configured-test-secret')
    assert main(['--home', str(tmp_path), 'patents', 'connect-status']) == 0
    response = json.loads(capsys.readouterr().out)
    assert response['connected_count'] == 0
    assert any(x['id'] == 'epo-ops' and x['configured'] and not x['connected'] for x in response['sources'])
    assert response['verified_live'] is False


def test_fetch_requires_online_and_imports_real_normalized_record(tmp_path, capsys, monkeypatch):
    from pineal import cli
    seen=[]
    def fetched(pub, *, source, **kwargs):
        seen.append((pub, source))
        return sample(pub)
    monkeypatch.setattr(cli, 'fetch_patent', fetched)
    home=str(tmp_path)
    assert main(['--home', home, 'patents', 'fetch', 'US20260305554A1', '--source', 'epo-ops']) == 2
    assert seen == []
    capsys.readouterr()
    assert main(['--home', home, 'patents', 'fetch', 'US20260305554A1', '--source', 'epo-ops', '--online']) == 0
    result=json.loads(capsys.readouterr().out)
    assert result['import']['inserted'] == 1
    assert result['record']['publication_id'] == 'US20260305554A1'
    assert seen == [('US20260305554A1','epo-ops')]
    assert main(['--home', home, 'patents', 'fetch', 'US20260305554A1', '--source', 'epo-ops', '--online']) == 0
    assert json.loads(capsys.readouterr().out)['import']['skipped'] == 1


def test_sync_preview_does_not_fetch_even_with_online(tmp_path, capsys, monkeypatch):
    from pineal import cli
    path=tmp_path/'ids.txt'
    path.write_text('US20260305554A1\nUS20260313851A1\n')
    monkeypatch.setattr(cli, 'fetch_patent', lambda *a, **k: pytest.fail('network forbidden in dry-run'))
    assert main(['--home', str(tmp_path/'state'), 'patents', 'sync', str(path),
                 '--source', 'epo-ops', '--dry-run', '--online']) == 0
    response=json.loads(capsys.readouterr().out)
    assert response['preview_only'] is True
    assert response['planned_count'] == 2
    assert PinealStore(tmp_path/'state'/'pineal.sqlite3').patent_stats()['total'] == 0


def test_sync_fetches_sequentially_then_imports_atomically(tmp_path, capsys, monkeypatch):
    from pineal import cli
    path=tmp_path/'ids.txt'
    path.write_text('US20260305554A1\nUS20260313851A1\n')
    seen=[]
    def fetch(pub, **kwargs):
        seen.append(pub)
        return sample(pub)
    monkeypatch.setattr(cli, 'fetch_patent', fetch)
    assert main(['--home', str(tmp_path/'ok'), 'patents', 'sync', str(path), '--online', '--source', 'epo-ops']) == 0
    response=json.loads(capsys.readouterr().out)
    assert response['import']['inserted'] == 2
    assert seen == ['US20260305554A1','US20260313851A1']
    assert PinealStore(tmp_path/'ok'/'pineal.sqlite3').patent_stats()['total'] == 2
    assert PinealStore(tmp_path/'ok'/'pineal.sqlite3').verify_audit()['ok']
    def fail_second(pub, **kwargs):
        if pub.endswith('3851A1'):
            raise ValueError('provider unavailable')
        return sample(pub)
    monkeypatch.setattr(cli, 'fetch_patent', fail_second)
    assert main(['--home', str(tmp_path/'bad'), 'patents', 'sync', str(path), '--online', '--source', 'epo-ops']) == 2
    assert PinealStore(tmp_path/'bad'/'pineal.sqlite3').patent_stats()['total'] == 0


def test_sync_rejects_oversize_duplicate_and_malformed_before_request(tmp_path, monkeypatch):
    from pineal import cli
    called=[]
    monkeypatch.setattr(cli, 'fetch_patent', lambda *args, **kwargs: called.append(1))
    examples = [
        'US20260305554A1\nUS20260305554A1\n',
        'not-a-patent\n',
        'US20260305554A1\nUS20260313851A1\n',
    ]
    for idx,text in enumerate(examples):
        path = tmp_path/f'{idx}.txt'
        path.write_text(text)
        args = ['--home', str(tmp_path/f'{idx}'), 'patents', 'sync', str(path), '--source', 'epo-ops', '--online']
        if idx == 2:
            args.extend(['--limit','1'])
        assert main(args) == 2
    assert called == []
    path=tmp_path/'big.txt'
    path.write_text('x' * 4097)
    assert main(['--home', str(tmp_path/'big'), 'patents', 'sync', str(path), '--online']) == 2
    assert called == []


def test_sources_catalog_includes_live_capable_providers(tmp_path, capsys):
    assert main(['--home', str(tmp_path), 'patents', 'sources']) == 0
    response = json.loads(capsys.readouterr().out)
    ids = {row['id'] for row in response['sources']}
    assert {'epo-linked-open', 'epo-ops', 'patentsview-us', 'wipo-patentscope', 'uspto-odp'} <= ids
    assert response['connected_count'] == 0
    assert response['globally_complete'] is False


def test_fetch_refuses_provider_publication_mismatch_without_import(tmp_path, capsys, monkeypatch):
    from pineal import cli
    monkeypatch.setattr(cli, 'fetch_patent', lambda _pub, **_k: sample('US20260313851A1'))
    home = tmp_path / 'state'
    assert main(['--home', str(home), 'patents', 'fetch', 'US20260305554A1',
                 '--source', 'epo-ops', '--online']) == 2
    assert 'mismatch' in capsys.readouterr().err
    assert PinealStore(home / 'pineal.sqlite3').patent_stats()['total'] == 0
