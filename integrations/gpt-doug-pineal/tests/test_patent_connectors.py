"""Behavioral contracts for explicitly authorized patent metadata adapters."""
import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from pineal.patent_connectors import (
    fetch_ops_publication, fetch_patentsview_grant, fetch_patent,
    patent_connection_status,
)


XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org" xmlns:ep="http://www.epo.org/exchange">
<ep:exchange-documents>
<ep:exchange-document country="US" doc-number="20260305554" kind="A1">
  <ep:bibliographic-data><ep:publication-reference><ep:document-id><ep:country>US</ep:country><ep:doc-number>20260305554</ep:doc-number><ep:kind>A1</ep:kind><ep:date>20261008</ep:date></ep:document-id></ep:publication-reference>
  <ep:invention-title lang="en">Plants and Seeds of Hybrid Corn Variety CH894993</ep:invention-title></ep:bibliographic-data>
  <ep:abstract lang="en"><ep:p>Patent disclosure describing hybrid corn.</ep:p></ep:abstract>
</ep:exchange-document></ep:exchange-documents></ops:world-patent-data>'''


class Response:
    def __init__(self, data, url):
        self.buffer = io.BytesIO(data)
        self.url = url

    def read(self, size=-1):
        return self.buffer.read(size)

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def ops_loader(xml=XML, change_url=None, token='token-test'):
    calls = []

    def open_request(request, timeout):
        calls.append(request)
        assert timeout == 8
        if request.full_url.endswith('/accesstoken'):
            assert request.get_method() == 'POST'
            assert request.data == b'grant_type=client_credentials'
            assert request.get_header('Authorization').startswith('Basic ')
            return Response(json.dumps({'access_token': token, 'expires_in': '1200'}).encode(),
                            'https://ops.epo.org/3.2/auth/accesstoken')
        assert request.get_method() == 'GET'
        assert request.get_header('Authorization') == 'Bearer ' + token
        assert request.full_url.endswith('/published-data/publication/docdb/US.20260305554.A1/biblio')
        return Response(xml, change_url or request.full_url)

    return open_request, calls


def test_ops_requires_credentials_before_network():
    attempted = []

    def fail(*_a, **_kw):
        attempted.append(1)
        raise AssertionError('no outbound request allowed')

    with pytest.raises(ValueError, match='EPO_OPS_KEY'):
        fetch_ops_publication('US20260305554A1', environ={}, opener=fail)
    assert attempted == []


def test_ops_token_exchange_and_real_xml_fields_to_existing_schema():
    opener, requests = ops_loader()
    p = fetch_ops_publication('US 2026/0305554 A1', opener=opener,
                              environ={'EPO_OPS_KEY': 'id', 'EPO_OPS_SECRET': 'secret'})
    assert len(requests) == 2
    assert p['publication_id'] == 'US20260305554A1'
    assert p['publication_date'] == '2026-10-08'
    assert p['title'] == 'Plants and Seeds of Hybrid Corn Variety CH894993'
    assert p['source'] == 'EPO Open Patent Services (OPS)'
    assert p['evidence_level'] == 'patent_disclosure_not_scientific_validation'
    assert p['source_url'].startswith('https://ops.epo.org/')


@pytest.mark.parametrize('bad_xml', [
    XML.replace(b'20260305554', b'20260305555'),
    b'<!DOCTYPE r [<!ENTITY x "hello">]><r>&x;</r>',
    b'<broken/>',
    b'a' * (256 * 1024 + 1),
])
def test_ops_rejects_wrong_id_xml_entities_missing_metadata_and_oversize(bad_xml):
    opener, _ = ops_loader(bad_xml)
    with pytest.raises(ValueError):
        fetch_ops_publication('US20260305554A1', opener=opener,
                              environ={'EPO_OPS_KEY': 'id', 'EPO_OPS_SECRET': 'secret'})


def test_ops_rejects_auth_and_publication_redirects_without_leaking_token():
    opener, _ = ops_loader(change_url='https://evil.example/steal')
    with pytest.raises(ValueError, match='source') as err:
        fetch_ops_publication('US20260305554A1', opener=opener,
                              environ={'EPO_OPS_KEY': 'id', 'EPO_OPS_SECRET': 'secret'})
    assert 'secret' not in str(err.value)
    assert 'token-test' not in str(err.value)


def grants_loader(payload=None, other_url=None):
    result = payload if payload is not None else {
        'error': False, 'count': 1, 'patents': [
            {'patent_id': '12345678', 'patent_title': 'Optical biosensor circuit',
             'patent_date': '2025-04-08', 'patent_abstract': 'Device patent disclosure.'},
        ]}
    calls = []

    def run(request, timeout):
        calls.append(request)
        assert timeout == 8
        assert request.get_header('X-api-key') == 'test-api-key'
        assert request.get_method() == 'GET'
        parsed = urlsplit(request.full_url)
        assert parsed.hostname == 'search.patentsview.org'
        query = parse_qs(parsed.query)
        assert json.loads(query['q'][0]) == {'patent_id': '12345678'}
        assert 'patent_title' in json.loads(query['f'][0])
        return Response(json.dumps(result).encode(), other_url or request.full_url)
    return run, calls


def test_patentsview_grant_query_and_importable_metadata():
    opener, calls = grants_loader()
    p = fetch_patentsview_grant('US12345678B2', opener=opener,
                               environ={'PATENTSVIEW_API_KEY': 'test-api-key'})
    assert len(calls) == 1
    assert p['publication_id'] == 'US12345678B2'
    assert p['source'] == 'PatentsView US PatentSearch API'
    assert p['publication_date'] == '2025-04-08'
    assert p['title'] == 'Optical biosensor circuit'
    assert p['source_url'] == 'https://patents.google.com/patent/US12345678B2/en'


def test_patentsview_rejects_publication_applications_or_wrong_ids():
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise AssertionError('must not make request')

    for pub in ['US20260305554A1', 'EP0084638A1', 'WO2025000200A1']:
        with pytest.raises(ValueError):
            fetch_patentsview_grant(pub, environ={'PATENTSVIEW_API_KEY': 'abc'}, opener=fail)
    with pytest.raises(ValueError, match='PATENTSVIEW_API_KEY'):
        fetch_patentsview_grant('US12345678B2', environ={}, opener=fail)
    assert calls == []
    opener, _ = grants_loader({'error': False, 'patents': [{'patent_id': '999', 'patent_title': 'wrong', 'patent_date': '2025-01-01'}]})
    with pytest.raises(ValueError, match='mismatch'):
        fetch_patentsview_grant('US12345678B2', environ={'PATENTSVIEW_API_KEY': 'test-api-key'}, opener=opener)


def test_patentsview_prevents_other_hosts_and_bad_provider_responses():
    opener, _ = grants_loader(other_url='https://evil.example/redirect')
    with pytest.raises(ValueError, match='source'):
        fetch_patentsview_grant('US12345678B2', environ={'PATENTSVIEW_API_KEY': 'test-api-key'}, opener=opener)
    opener, _ = grants_loader({'error': True, 'patents': []})
    with pytest.raises(ValueError):
        fetch_patentsview_grant('US12345678B2', environ={'PATENTSVIEW_API_KEY': 'test-api-key'}, opener=opener)


def test_routing_is_explicit_and_source_status_does_not_pretend_verification(monkeypatch):
    from pineal import patent_connectors as client
    calls = []

    def fake(pub, **kwargs):
        calls.append(pub)
        return {'publication_id': pub, 'source': 'fake'}

    monkeypatch.setattr(client, 'fetch_ops_publication', fake)
    assert fetch_patent('WO2025000200A1', source='epo-ops', environ={'EPO_OPS_KEY': 'x', 'EPO_OPS_SECRET': 'y'})['source'] == 'fake'
    assert calls == ['WO2025000200A1']
    with pytest.raises(ValueError, match='not supported'):
        fetch_patent('WO2025000200A1', source='wipo-patentscope')
    sources = {r['id']: r for r in patent_connection_status(environ={'EPO_OPS_KEY': 'x', 'EPO_OPS_SECRET': 'y'})}
    assert sources['epo-ops']['configured'] is True
    assert sources['epo-ops']['connected'] is False
    assert sources['patentsview-us']['configured'] is False
    assert sources['wipo-patentscope']['automated_scraping_permitted'] is False
