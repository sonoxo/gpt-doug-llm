import pytest

from pineal.store import PinealStore


def test_observation_is_versionless_append_only_and_audited(tmp_path):
    store = PinealStore(tmp_path / 'local.sqlite3')
    first = store.record_observation(node='global-trade', metric='shipping_index', value=114.0,
                                     unit='index', source='authorized-local-export')
    second = store.record_observation(node='global-trade', metric='shipping_index', value=119.0,
                                      unit='index', source='authorized-local-export')
    assert first['kind'] == 'local-manual'
    assert second['seq'] > first['seq']
    assert [r['value'] for r in store.list_observations(node='global-trade', limit=2)] == [119.0, 114.0]
    assert store.verify_audit()['checked'] == 2
    assert store.verify_audit()['ok']


def test_rejected_observation_cannot_mutate_state(tmp_path):
    store = PinealStore(tmp_path / 'local.sqlite3')
    with pytest.raises(ValueError):
        store.record_observation(node='warfighter-defense-si', metric='targeting',
                                 value=10.0, unit='count', source='manual', synthetic=False)
    assert store.list_observations() == []
    assert store.verify_audit()['checked'] == 0


def test_samples_separated_by_source_and_node(tmp_path):
    store = PinealStore(tmp_path / 'local.sqlite3')
    store.record_observation(node='global-markets', metric='volatility_index', value=20,
                             unit='index', source='public-manual')
    store.record_observation(node='biotech', metric='study_count', value=130,
                             unit='count', source='public-manual')
    assert len(store.list_observations(node='biotech')) == 1
    assert store.list_observations(node='biotech')[0]['classification'] == 'PUBLIC'
    with pytest.raises(ValueError):
        store.list_observations(node='unknown')
    with pytest.raises(ValueError):
        store.list_observations(limit=1001)
