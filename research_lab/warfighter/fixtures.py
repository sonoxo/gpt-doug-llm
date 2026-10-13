"""Load bounded, explicitly synthetic, offline Warfighter exercise inputs."""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

METRICS = frozenset({'training_readiness_pct','patch_compliance_pct','sensor_health_pct',
                     'zero_trust_coverage_pct','simulation_alerts'})
ROOT_FIELDS = frozenset({'schema_version','scenario_id','source_kind','classification',
                         'synthetic','domains','fixture','assumptions','model_id','seed'})
SAFE_TEXT = re.compile(r'[a-zA-Z0-9 .,_():/-]{1,256}\Z')


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                          allow_nan=False).encode('ascii')
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('non-canonical input') from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_scenario(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != ROOT_FIELDS:
        raise ValueError('scenario has missing or unknown fields')
    if (payload['schema_version'] != '1.0.0' or payload['source_kind'] != 'SYNTHETIC'
            or payload['classification'] != 'SYNTHETIC' or payload['synthetic'] is not True):
        raise ValueError('warfighter scenarios must be explicitly synthetic')
    if not isinstance(payload['scenario_id'],str) or not re.fullmatch(r'wr:scenario:[a-zA-Z0-9._-]{1,80}',payload['scenario_id']):
        raise ValueError('invalid scenario id')
    if type(payload['seed']) is not int or not 0 <= payload['seed'] <= 2**32-1:
        raise ValueError('seed out of bounds')
    domains=payload['domains']
    if (not isinstance(domains,list) or not domains or len(domains)>6 or
        len(set(str(x) for x in domains))!=len(domains) or
        any(x not in {'training','defensive-systems','maintenance','logistics','communications','continuity'} for x in domains)):
        raise ValueError('invalid research domain')
    metrics=payload['fixture']
    if not isinstance(metrics,dict) or not metrics or not set(metrics).issubset(METRICS):
        raise ValueError('unapproved aggregate metric')
    for name,value in metrics.items():
        if type(value) is not int or (not 0<=value<=100 if name.endswith('_pct') else not 0<=value<=1000000):
            raise ValueError('metric must be a bounded synthetic integer')
    assumptions=payload['assumptions']
    if not isinstance(assumptions,list) or not assumptions or len(assumptions)>12:
        raise ValueError('assumptions required')
    if not all(isinstance(x,str) and SAFE_TEXT.fullmatch(x) for x in assumptions):
        raise ValueError('unsafe assumptions')
    if not isinstance(payload['model_id'],str) or payload['model_id']!='synthetic-baseline-v1':
        raise ValueError('unsupported baseline model')
    if len(canonical_json(payload))>65536:
        raise ValueError('scenario too large')
    return json.loads(canonical_json(payload))


def load_scenario(path: Path, *, allowed_root: Path) -> dict[str,Any]:
    path=Path(path)
    root=Path(allowed_root).resolve(strict=True)
    if path.is_symlink():
        raise ValueError('symlink inputs prohibited')
    try:
        actual=path.resolve(strict=True)
    except OSError as exc:
        raise ValueError('scenario not found or inaccessible') from exc
    if not actual.is_relative_to(root):
        raise ValueError('scenario outside permitted directory')
    if not actual.is_file() or actual.stat().st_size>65536:
        raise ValueError('scenario missing or oversized')
    try:
        value=json.loads(actual.read_text(encoding='utf-8'),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite literal')))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('invalid utf8/json') from exc
    return validate_scenario(value)
