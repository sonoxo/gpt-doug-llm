"""The Mac status and loopback API must label configuration versus connectivity."""
import threading
from urllib.request import Request, urlopen
import json

from pineal.http_api import PinealHTTPServer
from pineal.store import PinealStore
from pineal.blink import render_blink
from pineal.dashboard import render_dashboard


def test_terminal_visuals_disclose_configured_but_not_connected(tmp_path, monkeypatch):
    monkeypatch.setenv('EPO_OPS_KEY', 'configured-test-key')
    monkeypatch.setenv('EPO_OPS_SECRET', 'configured-test-secret')
    store = PinealStore(tmp_path / 'state.db')
    blink = render_blink(store)
    dashboard = render_dashboard(store)
    assert 'OPS: CONFIGURED' in blink
    assert 'LIVE VERIFIED: 0' in blink
    assert 'PATENT FEEDS' in dashboard
    assert 'not live verified' in dashboard.lower()
    assert store.verify_audit()['checked'] == 0


def test_loopback_patent_source_status_is_authenticated_and_not_live(tmp_path, monkeypatch):
    monkeypatch.setenv('PATENTSVIEW_API_KEY', 'unit-test-key')
    token = 'local-test-secret-should-never-leave-loopback-12345'
    service = PinealHTTPServer(('127.0.0.1', 0), PinealStore(tmp_path / 'state.db'), token)
    worker = threading.Thread(target=service.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(f'http://127.0.0.1:{service.server_port}/v1/patents/sources',
                          headers={'Authorization': 'Bearer ' + token})
        with urlopen(request, timeout=5) as response:
            result = json.load(response)
        sources = {s['id']: s for s in result['sources']}
        assert result['connected_count'] == 0
        assert sources['patentsview-us']['configured'] is True
        assert sources['patentsview-us']['connected'] is False
        assert sources['epo-ops']['connected'] is False
        assert result['verified_live'] is False
    finally:
        service.shutdown()
        service.server_close()
        worker.join(timeout=2)
