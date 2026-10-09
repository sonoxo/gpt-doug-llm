import io
import json

import pytest

from pineal.cli import main
from pineal.dashboard import render_dashboard, run_dashboard
from pineal.store import PinealStore


def test_live_dashboard_shows_every_node_but_no_false_live_access(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    screen = render_dashboard(store, demo=False, color=False, width=105)
    assert 'META' in screen.upper()
    assert 'TESLA' in screen.upper()
    assert 'SNAPCHAT' in screen.upper()
    assert 'LINKEDIN' in screen.upper()
    assert 'GLOBAL TRADE' in screen.upper()
    assert 'WARFIGHTER' in screen.upper()
    assert 'NOT CONNECTED' in screen
    assert 'NO LIVE PROVIDER FEEDS' in screen
    assert 'SYNTHETIC DEMONSTRATION' not in screen
    assert '\x1b[' not in screen


def test_demo_is_explicitly_synthetic_and_does_not_write(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    screen = render_dashboard(store, demo=True, color=False, width=105)
    assert 'SYNTHETIC DEMONSTRATION' in screen
    assert 'DEMO' in screen
    assert 'GPU' in screen.upper()
    assert 'READINESS' in screen.upper()
    assert store.list_observations() == []
    assert store.verify_audit()['checked'] == 0


def test_audited_manual_metric_does_not_establish_connection(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    store.record_observation(node='global-markets', metric='volatility_index',
                             value=19.8, unit='index', source='licensed-daily-export')
    screen = render_dashboard(store, color=False, width=100)
    assert 'volatility_index' in screen
    assert '19.8' in screen
    assert 'LOCAL' in screen
    assert 'NOT CONNECTED' in screen
    assert 'AUDIT' in screen
    assert 'licensed-daily-export' in screen


def test_noninteractive_bounded_frames_never_clear_terminal(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    buf = io.StringIO()
    assert run_dashboard(store, demo=True, watch=True, interval=0.01, frames=2,
                         color=False, stream=buf) == 0
    result = buf.getvalue()
    assert result.count('ZYRA FEDERATION') == 2
    assert '\x1b[' not in result
    with pytest.raises(ValueError):
        run_dashboard(store, watch=True, interval=0, frames=2, stream=buf)


def test_cli_federation_observe_and_dashboard(tmp_path, capsys):
    home = str(tmp_path / 'state')
    assert main(['--home', home, 'federation']) == 0
    nodes = json.loads(capsys.readouterr().out)
    assert nodes['connected_count'] == 0
    assert main(['--home', home, 'observe', 'global-trade', 'shipping_index', '108.3',
                 '--unit', 'index', '--source', 'user-owned-csv']) == 0
    row = json.loads(capsys.readouterr().out)
    assert row['kind'] == 'local-manual'
    assert main(['--home', home, 'dashboard', '--no-color']) == 0
    out = capsys.readouterr().out
    assert 'shipping_index' in out
    assert 'NOT CONNECTED' in out


def test_cli_defense_refuses_nonsynthetic_and_unknown_node(tmp_path, capsys):
    home = str(tmp_path / 'state')
    args = ['--home', home, 'observe', 'warfighter-defense-si', 'sensor_health_pct',
            '92', '--unit', '%', '--source', 'exercise']
    assert main(args) == 2
    assert 'synthetic training' in capsys.readouterr().err
    assert main(args + ['--synthetic']) == 0
    assert json.loads(capsys.readouterr().out)['kind'] == 'synthetic'
    assert main(['--home', home, 'observe', 'unknown-node', 'shipping_index',
                 '10', '--source', 'exercise']) == 2
    assert 'unrecognized' in capsys.readouterr().err


def test_demo_watch_changes_visual_signal_without_external_data(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    first = render_dashboard(store, demo=True, color=False, frame=0)
    second = render_dashboard(store, demo=True, color=False, frame=1)
    assert first != second
    assert 'FEDERATION TOPOLOGY' in first
    assert 'POLICY + PROVENANCE + AUDIT' in first
    assert store.list_observations() == []
