import io
import json
from urllib.request import Request

import pytest

from pineal.patents import fetch_ep_metadata, list_sources


def test_registry_is_honest_about_auth_completeness_and_wipo_scraping():
    sources = {s['id']: s for s in list_sources()}
    assert {'epo-linked-open', 'uspto-odp', 'wipo-patentscope', 'worldwide-local-import'} <= set(sources)
    assert sources['epo-linked-open']['mode'] == 'single_document_opt_in'
    assert sources['uspto-odp']['requires_key'] is True
    assert sources['wipo-patentscope']['automated_scraping_permitted'] is False
    assert all(s['connected'] is False for s in sources.values())
    assert all(s['all_patents_covered'] is False for s in sources.values())


class Response:
    def __init__(self, payload, url='https://data.epo.org/linked-data/data/publication/EP/0084638/A1/-.json'):
        self.buffer = io.BytesIO(payload)
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, n):
        return self.buffer.read(n)

    def geturl(self):
        return self.url


def mocked(data, url=None):
    def loader(request, timeout):
        assert timeout == 8
        assert request.full_url.startswith('https://data.epo.org/linked-data/data/publication/EP/0084638/A1/')
        assert request.get_method() == 'GET'
        return Response(json.dumps(data).encode('utf-8'), url or 'https://data.epo.org/linked-data/data/publication/EP/0084638/A1/-.json')
    return loader


def test_single_official_ep_document_can_be_normalized_without_credentials():
    fixture = {'result': {'items': [{
        'titleOfInvention': {'_value': 'Cell metabolism research'},
        'publicationDate': '2024-06-05',
        'abstract': {'_value': 'Metadata from patent disclosure.'}}]}}
    record = fetch_ep_metadata('EP 0084638 A1', opener=mocked(fixture))
    assert record['publication_id'] == 'EP0084638A1'
    assert record['title'] == 'Cell metabolism research'
    assert record['publication_date'] == '2024-06-05'
    assert record['source'] == 'EPO Linked Open Data'
    assert record['evidence_level'] == 'patent_disclosure_not_scientific_validation'


def test_non_ep_or_invalid_ep_identifiers_never_trigger_network():
    attempts = []
    def fail(request, timeout):
        attempts.append(request)
        raise AssertionError('must not fetch')
    for value in ('US20260313851A1', 'EP__invalid', 'WO2025000100A1'):
        with pytest.raises(ValueError):
            fetch_ep_metadata(value, opener=fail)
    assert attempts == []


def test_external_redirect_final_hostname_missing_data_and_bounded_payload():
    fixture = {'result': {'items': [{'titleOfInvention': 'Valid', 'publicationDate': '2024-06-05'}]}}
    with pytest.raises(ValueError, match='redirect'):
        fetch_ep_metadata('EP0084638A1', opener=mocked(fixture, url='https://unsafe.example/other'))
    with pytest.raises(ValueError, match='metadata'):
        fetch_ep_metadata('EP0084638A1', opener=mocked({'result': {'items': []}}))
    large = {'result': {'items': [{'titleOfInvention': 'x' * 200000, 'publicationDate': '2024-06-05'}]}}
    with pytest.raises(ValueError, match='response size'):
        fetch_ep_metadata('EP0084638A1', opener=mocked(large))


def test_redirect_handler_blocks_cross_domain_before_follow():
    from pineal.patents import NoRedirect
    assert NoRedirect().redirect_request(Request('https://data.epo.org/'), None, 302, 'Moved', {'Location': 'https://unsafe.example/'}, 'https://unsafe.example/') is None
