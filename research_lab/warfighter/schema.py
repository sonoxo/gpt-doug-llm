"""WARFIGHTER_RESEARCH_V1 typed research graph; never operational authority."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SCHEMA_PATH = Path(__file__).resolve().parents[2] / 'safety-shield' / 'ontology' / 'warfighter-research-v1.json'
COMMON = frozenset({'id', 'schema_version', 'type', 'source_kind', 'classification',
                    'synthetic', 'created_at', 'provenance', 'source_refs',
                    'evidence_status', 'confidence_scope', 'record_sha256'})
ID = re.compile(r'wr:[a-z][a-z0-9-]{1,49}:[a-zA-Z0-9._-]{1,80}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
STATUS = frozenset({'UNSUBSTANTIATED','COMPUTED_UNVERIFIED','MATHEMATICALLY_VERIFIED',
                    'HUMAN_REVIEWED','REJECTED','REVOKED'})


def load_schema(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SCHEMA_PATH
    if target.stat().st_size > 65536:
        raise ValueError('schema exceeds file limit')
    value = json.loads(target.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('ontology_id') != 'WARFIGHTER_RESEARCH_V1'
            or value.get('authority') != 'RESEARCH_ONLY'):
        raise ValueError('unknown/untrusted ontology schema')
    return value


def _text(value: Any, name: str, max_len: int = 512) -> None:
    if not isinstance(value, str) or not value or len(value) > max_len or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'invalid {name}')


def validate_record(record: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError('record must be an object')
    kind = record.get('type')
    if kind not in schema['object_types']:
        raise ValueError('unrecognized research object type')
    required = COMMON | set(schema['object_types'][kind])
    if set(record) != required:
        raise ValueError('missing or forbidden record fields')
    if not ID.fullmatch(str(record['id'])) or not record['id'].startswith('wr:' + kind.lower() + ':'):
        raise ValueError('invalid namespaced id')
    if (record['schema_version'] != schema['version'] or
            record['source_kind'] != 'SYNTHETIC' or record['classification'] != 'SYNTHETIC'
            or record['synthetic'] is not True):
        raise ValueError('only synthetic research records are accepted')
    for key in ('provenance','confidence_scope'):
        _text(record[key], key)
    if record['evidence_status'] not in STATUS:
        raise ValueError('unrecognized evidence status')
    if not isinstance(record['source_refs'], list) or not 1 <= len(record['source_refs']) <= 20:
        raise ValueError('source_refs must be a nonempty bounded list')
    for ref in record['source_refs']:
        _text(ref, 'source_ref', 256)
    if not isinstance(record['record_sha256'], str) or not SHA.fullmatch(record['record_sha256']):
        raise ValueError('invalid sha256 format')
    try:
        stamp = datetime.fromisoformat(record['created_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('timezone required')
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('invalid created_at timestamp') from exc
    for key in schema['object_types'][kind]:
        value = record[key]
        if isinstance(value, str):
            _text(value, key, 1024)
        elif isinstance(value, list):
            if not value or len(value) > 20 or any(not isinstance(v, str) or not v or len(v) > 1024 for v in value):
                raise ValueError('invalid list field: ' + key)
        elif type(value) is int:
            if not -1000000 <= value <= 1000000:
                raise ValueError('numeric field outside limit')
        else:
            raise ValueError('invalid field type: ' + key)
        if key.endswith('_pct') and (type(value) is not int or not 0 <= value <= 100):
            raise ValueError('percent outside 0..100')
    return dict(record)


def validate_graph(nodes: list[dict], edges: list[dict], schema: Mapping[str, Any]) -> None:
    if (not isinstance(nodes,list) or len(nodes) > 100 or not isinstance(edges,list)
            or len(edges) > 500):
        raise ValueError('graph exceeds caps')
    entries={}
    for node in nodes:
        item=validate_record(node,schema)
        if item['id'] in entries:
            raise ValueError('duplicate graph object')
        entries[item['id']]=item
    seen=set()
    for edge in edges:
        if not isinstance(edge,dict) or set(edge) != {'from','predicate','to'}:
            raise ValueError('invalid graph edge')
        pred=edge['predicate']
        allowed=schema['edge_types'].get(pred)
        if not allowed or edge['from'] not in entries or edge['to'] not in entries:
            raise ValueError('unknown graph relationship or endpoint')
        if (entries[edge['from']]['type'] != allowed['from'] or
                entries[edge['to']]['type'] != allowed['to'] or edge['from']==edge['to']):
            raise ValueError('relationship type mismatch or self-link')
        identity=(edge['from'],pred,edge['to'])
        if identity in seen:
            raise ValueError('duplicate edge')
        seen.add(identity)
