"""Opt-in, bounded patent metadata sources; no scraping, crawling or background fetches.

EPO OPS accepts worldwide publication IDs under a registered app's OAuth grant.
PatentsView accepts issued US grants under an existing API key. WIPO public
PATENTSCOPE, USPTO ODP and unlicensed feeds are NOT accessed automatically.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from xml.etree import ElementTree

from .patents import NoRedirect, list_sources, normalize_publication_id, validate_record

_OPS_AUTH = 'https://ops.epo.org/3.2/auth/accesstoken'
_OPS_ROOT = 'https://ops.epo.org/3.2/rest-services/published-data/publication/docdb'
_PV_URL = 'https://search.patentsview.org/api/v1/patent/'
_MAX_AUTH = 16 * 1024
_MAX_XML = 256 * 1024
_MAX_JSON = 128 * 1024


def _https_bytes(request: Request, *, limit: int, opener=None, timeout: float = 8) -> bytes:
    """Read exactly one pinned HTTPS resource with redirects disabled, size capped."""
    target = request.full_url
    if not target.startswith('https://'):
        raise ValueError('official HTTPS source required')
    read = opener or build_opener(NoRedirect()).open
    try:
        with read(request, timeout=timeout) as response:
            if response.geturl() != target:
                raise ValueError('patent source changed location; redirect refused')
            body = response.read(limit + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # Deliberately avoid leaking URL, key or API errors into CLI/stdout.
        raise ValueError('official patent source unavailable or unauthorized') from None
    if len(body) > limit:
        raise ValueError('patent source response exceeds size limit')
    return body


def _tag(element) -> str:
    return str(element.tag).rsplit('}', 1)[-1]


def _first(element, tag: str):
    return next((child for child in element if _tag(child) == tag), None)


def _children(element, tag: str):
    return (child for child in element if _tag(child) == tag)


def _text(element) -> str:
    return ' '.join(''.join(element.itertext()).split()) if element is not None else ''


def _publication_xml(xml: bytes, publication_id: str, source_url: str) -> dict:
    if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
        raise ValueError('XML entity declarations are prohibited')
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        raise ValueError('invalid EPO OPS publication XML') from None
    match = re.fullmatch(r'([A-Z]{2})([0-9]{4,15})([ABCU][0-9]?)', publication_id)
    if match is None:
        raise ValueError('invalid publication identifier')
    country, number, kind = match.groups()
    for document in root.iter():
        if _tag(document) != 'exchange-document':
            continue
        if (document.attrib.get('country', '').upper() != country
                or document.attrib.get('doc-number', '').lstrip('0') != number.lstrip('0')
                or document.attrib.get('kind', '').upper() != kind):
            continue
        bib = _first(document, 'bibliographic-data')
        if bib is None:
            continue
        pubref = _first(bib, 'publication-reference')
        docid = _first(pubref, 'document-id') if pubref is not None else None
        date_node = _first(docid, 'date') if docid is not None else None
        when = _text(date_node)
        if not re.fullmatch(r'[0-9]{8}', when):
            raise ValueError('official publication date is unavailable')
        formatted = f'{when[:4]}-{when[4:6]}-{when[6:8]}'
        date.fromisoformat(formatted)
        titles = list(_children(bib, 'invention-title'))
        title = _text(next((t for t in titles if t.attrib.get('lang') == 'en'), titles[0] if titles else None))
        abstracts = list(_children(document, 'abstract'))
        abstract = _text(next((a for a in abstracts if a.attrib.get('lang') == 'en'), abstracts[0] if abstracts else None))
        if not title:
            raise ValueError('official patent title is unavailable')
        return validate_record({
            'publication_id': publication_id, 'title': title, 'publication_date': formatted,
            'abstract': abstract[:3000], 'source': 'EPO Open Patent Services (OPS)',
            'source_url': source_url, 'cpc': '', 'cell_tags': [],
        })
    raise ValueError('official EPO patent publication mismatch or unavailable')


def fetch_ops_publication(publication_id: str, *, opener=None,
                          environ=None, timeout: float = 8) -> dict:
    """Fetch one worldwide publication from EPO OPS with operator-owned OAuth keys."""
    pub = normalize_publication_id(publication_id)
    settings = os.environ if environ is None else environ
    key, secret = settings.get('EPO_OPS_KEY'), settings.get('EPO_OPS_SECRET')
    if not (key and secret):
        raise ValueError('EPO_OPS_KEY and EPO_OPS_SECRET are required (no network request made)')
    if not isinstance(timeout, (float, int)) or not 1 <= timeout <= 15:
        raise ValueError('timeout must be 1-15 seconds')
    encoded = base64.b64encode(f'{key}:{secret}'.encode('utf-8')).decode('ascii')
    auth = Request(_OPS_AUTH, data=b'grant_type=client_credentials', method='POST',
                   headers={'Authorization': 'Basic ' + encoded,
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Accept': 'application/json', 'User-Agent': 'GPT-Doug-Pineal/0.4'})
    raw_token = _https_bytes(auth, limit=_MAX_AUTH, opener=opener, timeout=timeout)
    try:
        decoded = json.loads(raw_token)
        token = decoded['access_token']
        if (not isinstance(token, str) or not (1 <= len(token) <= 8192)
                or any(ch.isspace() or ord(ch) < 33 for ch in token)):
            raise ValueError('invalid access token')
    except (ValueError, KeyError, TypeError):
        raise ValueError('invalid EPO OAuth response') from None
    authority, number, kind = re.fullmatch(r'([A-Z]{2})([0-9]{4,15})([ABCU][0-9]?)', pub).groups()
    endpoint = f'{_OPS_ROOT}/{authority}.{number}.{kind}/biblio'
    request = Request(endpoint, headers={'Authorization': 'Bearer ' + token,
                                         'Accept': 'application/xml',
                                         'User-Agent': 'GPT-Doug-Pineal/0.4'})
    xml = _https_bytes(request, limit=_MAX_XML, opener=opener, timeout=timeout)
    return _publication_xml(xml, pub, endpoint)


def fetch_patentsview_grant(publication_id: str, *, opener=None,
                            environ=None, timeout: float = 8) -> dict:
    """Retrieve bibliographic metadata for a specified issued US grant only."""
    pub = normalize_publication_id(publication_id)
    match = re.fullmatch(r'US([0-9]{6,15})B[12]', pub)
    if not match:
        raise ValueError('PatentsView supports issued US B1/B2 grants, not A1 applications')
    settings = os.environ if environ is None else environ
    api_key = settings.get('PATENTSVIEW_API_KEY')
    if not api_key:
        raise ValueError('PATENTSVIEW_API_KEY is required (no network request made)')
    if not isinstance(timeout, (float, int)) or not 1 <= timeout <= 15:
        raise ValueError('timeout must be 1-15 seconds')
    number = match.group(1).lstrip('0')
    query = {'q': json.dumps({'patent_id': number}),
             'f': json.dumps(['patent_id', 'patent_title', 'patent_date', 'patent_abstract']),
             'o': json.dumps({'size': 1})}
    request = Request(_PV_URL + '?' + urlencode(query),
                      headers={'X-Api-Key': api_key, 'Accept': 'application/json',
                               'User-Agent': 'GPT-Doug-Pineal/0.4'})
    content = _https_bytes(request, limit=_MAX_JSON, opener=opener, timeout=timeout)
    try:
        response = json.loads(content)
        records = response['patents']
        if response.get('error') not in (False, None) or not isinstance(records, list) or len(records) != 1:
            raise ValueError('provider returned error or no exact record')
        found = records[0]
        if str(found['patent_id']).lstrip('0') != number:
            raise ValueError('PatentsView publication ID mismatch')
        return validate_record({
            'publication_id': pub, 'title': found['patent_title'],
            'publication_date': found['patent_date'],
            'abstract': str(found.get('patent_abstract') or '')[:3000],
            'source': 'PatentsView US PatentSearch API',
            'source_url': 'https://patents.google.com/patent/' + pub + '/en',
            'cpc': '', 'cell_tags': [],
        })
    except (KeyError, TypeError, IndexError, UnicodeError, json.JSONDecodeError):
        raise ValueError('invalid PatentsView response') from None


def patent_connection_status(*, environ=None) -> list[dict]:
    """Credential presence is NOT equivalent to an active or verified connection."""
    settings = os.environ if environ is None else environ
    options = list_sources() + [
        {'id': 'epo-ops', 'name': 'EPO OPS Worldwide', 'mode': 'single_document_opt_in',
         'requires_key': True, 'automated_scraping_permitted': False,
         'terms': 'App registration, OAuth and EPO OPS fair-use rules; limited lookups',
         'connected': False, 'all_patents_covered': False},
        {'id': 'patentsview-us', 'name': 'PatentsView US issued grants',
         'mode': 'single_grant_opt_in', 'requires_key': True,
         'automated_scraping_permitted': False, 'connected': False,
         'all_patents_covered': False,
         'terms': 'Existing PatentsView key and usage limits; US B1/B2 grants only'},
    ]
    configured = {'epo-ops': bool(settings.get('EPO_OPS_KEY') and settings.get('EPO_OPS_SECRET')),
                  'patentsview-us': bool(settings.get('PATENTSVIEW_API_KEY')),
                  'uspto-odp': bool(settings.get('USPTO_ODP_API_KEY'))}
    return [{**source, 'configured': configured.get(source['id'], source['id'] == 'epo-linked-open'),
             'connection_state': 'not_live_verified'} for source in options]


def fetch_patent(publication_id: str, *, source: str = 'auto',
                 opener=None, environ=None, timeout: float = 8) -> dict:
    """Route an explicit single lookup; never silently scrape a fallback host."""
    pub = normalize_publication_id(publication_id)
    settings = os.environ if environ is None else environ
    if source == 'auto':
        if pub.startswith('EP'):
            source = 'epo-linked-open'
        elif pub.startswith('US') and re.fullmatch(r'US[0-9]+B[12]', pub) and settings.get('PATENTSVIEW_API_KEY'):
            source = 'patentsview-us'
        else:
            source = 'epo-ops'
    if source == 'epo-linked-open':
        from .patents import fetch_ep_metadata
        return fetch_ep_metadata(pub, opener=opener, timeout=timeout)
    if source == 'epo-ops':
        return fetch_ops_publication(pub, opener=opener, environ=settings, timeout=timeout)
    if source == 'patentsview-us':
        return fetch_patentsview_grant(pub, opener=opener, environ=settings, timeout=timeout)
    raise ValueError(f'patent source {source!r} not supported for live lookup; use authorized local import')


def load_publication_ids(path: str | Path, *, limit: int = 10) -> list[str]:
    """Read a small, explicit operator-supplied list; never infer a crawl."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('sync limit must be between 1 and 20')
    filename = Path(path).expanduser()
    if not filename.is_file():
        raise ValueError('publication ID list not found')
    with filename.open('rb') as handle:
        raw = handle.read(4097)
    if len(raw) > 4096:
        raise ValueError('publication ID list must be 4 KiB or smaller')
    try:
        lines = [line.strip() for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    except UnicodeError:
        raise ValueError('publication ID list must be UTF-8 text') from None
    if not (1 <= len(lines) <= limit):
        raise ValueError('publication ID count must be between 1 and sync limit')
    ids = [normalize_publication_id(line) for line in lines]
    if len(set(ids)) != len(ids):
        raise ValueError('publication IDs must be unique')
    return ids
