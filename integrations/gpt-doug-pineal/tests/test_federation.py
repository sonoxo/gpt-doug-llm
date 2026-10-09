"""Federation contract: no false external access and no sensitive data collection."""
import math

import pytest

from pineal.federation import list_nodes, validate_observation


def test_known_nodes_are_only_unconnected_templates():
    nodes = list_nodes()
    names = {node['id'] for node in nodes}
    assert {'zyra', 'meta', 'tesla', 'x', 'snapchat', 'linkedin',
            'global-trade', 'global-markets', 'biotech', 'warfighter-defense-si'} <= names
    assert all(node['connected'] is False for node in nodes)
    assert all(node['status'] in {'local-only', 'not-connected'} for node in nodes)


def test_public_manual_trade_observation_has_provenance():
    data = validate_observation('global-trade', 'shipping_index', 112.5, 'index',
                                'licensed-manual-export')
    assert data['node'] == 'global-trade'
    assert data['kind'] == 'local-manual'
    assert data['source'] == 'licensed-manual-export'
    assert data['classification'] == 'PUBLIC'
    assert data['value'] == 112.5


@pytest.mark.parametrize('node,metric,value,source', [
    ('meta-admin', 'followers', 100, 'manual'),
    ('x', 'trading;drop', 10, 'manual'),
    ('tesla', 'sales', float('nan'), 'manual'),
    ('tesla', 'sales', float('inf'), 'manual'),
    ('tesla', 'sales', True, 'manual'),
    ('meta', 'followers', 2, 'sk-123456789012345678901'),
    ('x', 'followers', 2, 'manual\x1b[31m'),
])
def test_invalid_and_sensitive_fields_are_rejected(node, metric, value, source):
    with pytest.raises(ValueError):
        validate_observation(node, metric, value, 'count', source)


@pytest.mark.parametrize('metric', ['target_location', 'weapons_payload', 'fire_control', 'raw_biometrics'])
def test_defense_never_accepts_offensive_or_private_subjects(metric):
    with pytest.raises(ValueError):
        validate_observation('warfighter-defense-si', metric, 95, '%', 'simulator', synthetic=True)


def test_defense_accepts_only_bounded_synthetic_readiness():
    with pytest.raises(ValueError):
        validate_observation('warfighter-defense-si', 'patch_compliance_pct', 91, '%', 'manual')
    report = validate_observation('warfighter-defense-si', 'patch_compliance_pct', 91, '%',
                                  'training-simulator', synthetic=True)
    assert report['kind'] == 'synthetic'
    assert report['node'] == 'warfighter-defense-si'


@pytest.mark.parametrize('metric', ['eeg_raw', 'brain_decoding', 'patient_identifier'])
def test_biotech_rejects_personal_neural_data(metric):
    with pytest.raises(ValueError):
        validate_observation('biotech', metric, 2, 'count', 'manual', synthetic=True)


def test_biotech_research_metrics_and_classification_gates():
    assert validate_observation('biotech', 'publications', 88, 'count', 'PubMed-manual')['kind'] == 'local-manual'
    with pytest.raises(ValueError):
        validate_observation('biotech', 'publications', 88, 'count', 'manual', classification='SECRET')
    with pytest.raises(ValueError):
        validate_observation('biotech', 'simulated_eeg_bandpower', 0.2, 'index', 'manual')
    assert validate_observation('biotech', 'simulated_eeg_bandpower', 0.2, 'index',
                                'research-simulator', synthetic=True)['kind'] == 'synthetic'
