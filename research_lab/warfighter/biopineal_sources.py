"""Read-only, provenance-labelled BioPINEAL research source index.

A public patent application and a vendor's biological-computing page are
independent references. This module never asserts shared inventorship,
ownership, hardware access, operational authority, or scientific validation.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

_REGISTRY = (Path(__file__).resolve().parents[2] / 'intel' / 'sources' /
             'biopineal-2026-10-12-public-evidence.json')
_TOP_FIELDS = frozenset({'schema_version', 'ontology_namespace', 'authority',
                          'source_set_kind', 'controls', 'records'})
_RECORD_FIELDS = frozenset({
    'id', 'record_kind', 'topic', 'document_number', 'title', 'publisher',
    'assignee', 'source_url', 'publication_date', 'capture_origin', 'capture_date',
    'source_capture_sha256', 'captured_search_query', 'evidence_state',
    'relationship_to_biopineal', 'authority', 'scientific_claims_verified',
    'patent_grant_verified', 'has_neural_biochip_claims',
    'cortical_labs_associated', 'connected_to_local_hardware',
    'associated_with_patent', 'related_parent_document', 'claims',
})
_CONTROLS = {
    'allow_network_access': False,
    'allow_operational_promotion': False,
    'allow_model_weight_modification': False,
    'allow_hardware_connection': False,
    'automatic_publication': False,
    'ownership_or_licensing_inferred': False,
    'cross_source_association_inferred': False,
}
_PATENT = 'us-pgpub:20260308339-A1'
_VENDOR = 'cortical-labs:cl1'
_SOURCE_HASH = 'fd01488625510df8bb52e0d27eb88e63c99fa0759ea0471b828ec3270ad5bfc9'
_PINNED_CANONICAL_HASH = 'd1f0b6e22454a9082aaa84f430d4979867d0418b954a4869a64aec4fff183e04'
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError('BioPINEAL source rejected: ' + message)


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _clean_text(value: Any, max_length: int = 250) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= max_length and
            not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _validate_record(record: Any) -> None:
    _require(isinstance(record, dict) and set(record) == _RECORD_FIELDS,
             'unknown or missing record fields')
    ident = record['id']
    _require(ident in {_PATENT, _VENDOR}, 'unknown reference ID')
    _require(record['authority'] == 'RESEARCH_ONLY', 'authority escalation')
    _require(record['scientific_claims_verified'] is False,
             'unverified science cannot be labeled proven')
    _require(record['connected_to_local_hardware'] is False, 'no local wetware connection')
    _require(record['patent_grant_verified'] is False, 'application is not a verified grant')
    for key in ('title', 'publisher', 'source_url', 'evidence_state',
                'relationship_to_biopineal', 'capture_origin', 'topic'):
        _require(_clean_text(record[key], 250), 'invalid ' + key)
    _require(isinstance(record['claims'], list) and
             1 <= len(record['claims']) <= 5 and
             all(_clean_text(item) for item in record['claims']),
             'claims must be short attributed summaries')
    _require(record['capture_date'] == '2026-10-12', 'unknown snapshot date')
    try:
        date.fromisoformat(record['capture_date'])
        if record['publication_date'] is not None:
            date.fromisoformat(record['publication_date'])
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid reference date') from exc
    if ident == _PATENT:
        pinned = {
            'record_kind': 'PUBLISHED_APPLICATION',
            'topic': 'bioassimilating_polymers',
            'document_number': 'US-20260308339-A1',
            'publisher': 'USPTO Patent Public Search (user-supplied capture)',
            'assignee': 'SMART PLASTIC TECHNOLOGIES, LLC',
            'source_url': 'https://ppubs.uspto.gov/',
            'publication_date': '2026-10-08',
            'capture_origin': 'USER_SUPPLIED_USPTO_TEXT',
            'source_capture_sha256': _SOURCE_HASH,
            'captured_search_query': 'cortical labs',
            'evidence_state': 'PATENT_DISCLOSURE_NOT_INDEPENDENTLY_VALIDATED',
            'relationship_to_biopineal': 'MATERIALS_SCIENCE_REFERENCE_ONLY',
            'has_neural_biochip_claims': False,
            'cortical_labs_associated': False,
            'associated_with_patent': True,
            'related_parent_document': 'US-12668672-B2',
        }
        _require(record['title'].startswith('BIO-ASSIMILATION MASTER BATCH'),
                 'patent identity mismatch')
    else:
        pinned = {
            'record_kind': 'FIRST_PARTY_VENDOR_REFERENCE',
            'topic': 'biological_computing',
            'document_number': None,
            'publisher': 'Cortical Labs',
            'assignee': None,
            'source_url': 'https://www.corticallabs.com/cl1.html',
            'publication_date': None,
            'capture_origin': 'FIRST_PARTY_VENDOR_WEBPAGE',
            'source_capture_sha256': None,
            'captured_search_query': None,
            'evidence_state': 'VENDOR_CLAIMS_NOT_INDEPENDENTLY_VALIDATED',
            'relationship_to_biopineal': 'EXTERNAL_BIOCOMPUTING_REFERENCE_ONLY',
            'has_neural_biochip_claims': True,
            'cortical_labs_associated': True,
            'associated_with_patent': False,
            'related_parent_document': None,
        }
        _require(record['title'] == 'CL1 biological computing platform',
                 'vendor product identity mismatch')
    for field, expected in pinned.items():
        actual = record[field]
        _require(type(actual) is type(expected) and actual == expected,
                 'unexpected evidence attribution or status: ' + field)
    _require(record['source_capture_sha256'] is None or
             bool(_SHA.fullmatch(record['source_capture_sha256'])),
             'capture digest format')


def load_sources(path: Path | None = None) -> dict[str, Any]:
    """Load one curated metadata registry without network, execution, or writes."""
    source = _REGISTRY if path is None else Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 65536:
        raise ValueError('BioPINEAL registry must be an ordinary JSON file <=64 KiB')
    try:
        raw = source.read_bytes()
        data = json.loads(raw.decode('utf-8'),
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite source value')))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid BioPINEAL source JSON') from exc
    _require(isinstance(data, dict) and set(data) == _TOP_FIELDS,
             'invalid registry schema')
    _require(data['schema_version'] == '1.0.0' and
             data['ontology_namespace'] == 'GPT_DOUG_BIOPINEAL_RESEARCH_SOURCES_V1' and
             data['authority'] == 'RESEARCH_ONLY' and
             data['source_set_kind'] == 'CURATED_EXTERNAL_REFERENCE_NOT_TECHNOLOGY_IMPLEMENTATION',
             'unexpected reference namespace or authority')
    _require(isinstance(data['controls'], dict) and
             set(data['controls']) == set(_CONTROLS) and
             all(data['controls'][k] is v for k, v in _CONTROLS.items()),
             'research-only access controls missing')
    entries = data['records']
    _require(isinstance(entries, list) and len(entries) == 2, 'only two curated sources in v1')
    for entry in entries:
        _validate_record(entry)
    _require({r['id'] for r in entries} == {_PATENT, _VENDOR},
             'missing or duplicate canonical source ID')
    _require(_hash(data) == _PINNED_CANONICAL_HASH,
             'source integrity mismatch with pinned curated research digest')
    for record in entries:
        record['record_sha256'] = _hash(record)
    data['registry_sha256'] = hashlib.sha256(raw).hexdigest()
    return data


def search_sources(query: str | None = None,
                   topic: str | None = None) -> dict[str, Any]:
    """Return explicitly non-authoritative external references, not search-result ownership."""
    if query is not None and (not isinstance(query, str) or len(query) > 128 or
                              any(ord(c) < 32 or ord(c) == 127 for c in query)):
        raise ValueError('query must be <=128 printable characters')
    if topic is not None and topic not in {'bioassimilating_polymers', 'biological_computing'}:
        raise ValueError('unsupported BioPINEAL reference topic')
    registry = load_sources()
    needle = (query or '').strip().casefold()
    selected = []
    for record in registry['records']:
        if topic is not None and record['topic'] != topic:
            continue
        # Captured search query deliberately EXCLUDED: it is NOT a factual link
        # between that search term and the patent surfaced in the results.
        searchable = ' '.join(str(x) for x in (
            record['title'], record['publisher'], record['assignee'],
            record['document_number'], record['topic'], *record['claims']
        )).casefold()
        if needle and needle not in searchable:
            continue
        selected.append(record)
    return {
        'system': 'GPT-Doug BioPINEAL External Research Sources',
        'ontology_namespace': registry['ontology_namespace'],
        'authority': 'RESEARCH_ONLY',
        'records': selected,
        'registry_sha256': registry['registry_sha256'],
        'external_calls': 0,
        'automated_publication': False,
        'hardware_connected': False,
        'scope': 'CURATED_EVIDENCE_NOT_AUTHORITY_OR_IMPLEMENTATION',
    }
