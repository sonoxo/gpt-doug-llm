import json

import pytest

from pineal.patents import load_records, normalize_publication_id, validate_record
from pineal.store import ConflictError, PinealStore


def sample(publication_id='US 2026/0313851 A1', title='Supplemental Power and Cooling'):
    return {'publication_id': publication_id, 'title': title,
            'publication_date': '2026-10-08', 'abstract': 'Cooling architecture for GPU server racks.',
            'source': 'uspto-public-metadata',
            'source_url': 'https://patents.google.com/patent/US20260313851A1/en',
            'cpc': 'H05K7/20772', 'cell_tags': []}


def test_normalizes_patent_id_and_enforces_unverified_disclosure():
    assert normalize_publication_id('US 2026/0313851 A1') == 'US20260313851A1'
    p = validate_record(sample())
    assert p['publication_id'] == 'US20260313851A1'
    assert p['jurisdiction'] == 'US'
    assert p['evidence_level'] == 'patent_disclosure_not_scientific_validation'
    assert p['cell_tags'] == []


@pytest.mark.parametrize('url', [
    'http://patents.google.com/patent/US20260313851A1',
    'https://patents.google.com.attacker.example/patent/US20260313851A1',
    'https://user:password@data.epo.org/linked-data/',
    'https://@data.epo.org/linked-data/',
    'https://127.0.0.1/patent/US20260313851A1',
    'https://patents.google.com:8080/patent/US20260313851A1',
    'https://patents.google.com/patent/US20260313851A1?token=123',
])
def test_untrusted_urls_fail_closed(url):
    record = sample()
    record['source_url'] = url
    with pytest.raises(ValueError):
        validate_record(record)


def test_rejects_unsupported_jurisdiction_invalid_date_or_cell_tag():
    for key, value in [('publication_id', 'XYZ10000A1'),
                       ('publication_date', '2026-02-30'),
                       ('cell_tags', ['generate_human_embryo'])]:
        record = sample()
        record[key] = value
        with pytest.raises(ValueError):
            validate_record(record)


def test_atomic_import_idempotence_search_and_provenance(tmp_path):
    store = PinealStore(tmp_path / 'store.sqlite3')
    r = sample()
    r2 = sample('EP 0084638 A1', 'Human tissue research bibliography')
    r2.update(source='epo-linked-data', source_url='https://data.epo.org/linked-data/data/publication/EP/0084638/A1/-',
              cell_tags=['neuron'])
    result = store.import_patents([r, r2])
    assert result == {'inserted': 2, 'skipped': 0, 'total': 2}
    assert store.import_patents([r])['skipped'] == 1
    hit = store.search_patents('human tissue')[0]
    assert hit['publication_id'] == 'EP0084638A1'
    assert hit['cell_tags'] == ['neuron']
    assert hit['source_url'].startswith('https://data.epo.org/')
    assert store.patent_stats()['total'] == 2
    assert store.patent_stats()['jurisdictions']['EP'] == 1
    assert store.verify_audit()['ok']
    assert store.verify_audit()['checked'] == 2


def test_conflicting_batch_rolls_back_every_patent(tmp_path):
    store = PinealStore(tmp_path / 'store.sqlite3')
    a = sample()
    conflict = sample(title='Tampered title')
    with pytest.raises(ConflictError):
        store.import_patents([a, conflict])
    assert store.patent_stats()['total'] == 0
    assert store.verify_audit()['checked'] == 0
    store.import_patents([a])
    with pytest.raises(ConflictError):
        store.import_patents([sample('EP 0084638 A1'), conflict])
    assert store.patent_stats()['total'] == 1
    assert store.verify_audit()['checked'] == 1


def test_jsonl_and_csv_import_are_bounded_and_validated_before_write(tmp_path):
    r = sample()
    f = tmp_path / 'records.jsonl'
    f.write_text(json.dumps(r) + '\n')
    assert load_records(f)[0]['publication_id'] == 'US20260313851A1'
    f.write_text(json.dumps(r) + '\n' + '{invalid}\n')
    with pytest.raises(ValueError):
        load_records(f)
    f.write_text('z' * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        load_records(f)
    csvfile = tmp_path / 'records.csv'
    csvfile.write_text('publication_id,title,publication_date,abstract,source,source_url,cpc,cell_tags\n'
                       'EP0084638A1,Neuron atlas,2026-10-08,Research metadata,EPO,https://data.epo.org/linked-data/data/publication/EP/0084638/A1/-,A61K,neuron\n')
    assert load_records(csvfile)[0]['cell_tags'] == ['neuron']


def test_patent_query_is_bounded_and_no_live_source_fabricated(tmp_path):
    store = PinealStore(tmp_path / 'memory.db')
    assert store.patent_stats()['total'] == 0
    assert store.search_patents('neurons') == []
    with pytest.raises(ValueError):
        store.search_patents('x' * 257)
    with pytest.raises(ValueError):
        store.search_patents('x', limit=0)


def test_date_must_use_explicit_iso_hyphenated_publication_format():
    r = sample()
    r['publication_date'] = '20261008'
    with pytest.raises(ValueError, match='YYYY-MM-DD'):
        validate_record(r)


def test_import_stops_decoding_before_unbounded_rows(tmp_path, monkeypatch):
    from pineal import patents
    records = tmp_path / 'too-many.jsonl'
    records.write_text(('{' + '"publication_id":"US20260313851A1"' + '}\n') * 1001)
    original = patents.json.loads
    calls = 0

    def counting_loads(row):
        nonlocal calls
        calls += 1
        return original(row)

    monkeypatch.setattr(patents.json, 'loads', counting_loads)
    with pytest.raises(ValueError):
        patents.load_records(records, limit=1000)
    assert calls <= 1000  # no traversal of arbitrary million-row inputs
