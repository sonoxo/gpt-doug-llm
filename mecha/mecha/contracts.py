"""Strict, canonical, synthetic-only MECHA exercise contracts."""
from __future__ import annotations
import hashlib
import json
import math
import re
from typing import Any, Mapping

ROOT_KEYS = frozenset({'schema_version','type','source_kind','authority','mode',
                       'synthetic','seed','robot','environment','assumptions'})
ROBOT_KEYS = frozenset({'id','class','pose','health_pct','power_budget_units'})
ENV_KEYS = frozenset({'terrain','obstacles'})
NAME = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
ASCII_TEXT = re.compile(r'[ -~]{1,256}\Z')


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                          allow_nan=False).encode('ascii')
    except (ValueError,TypeError,OverflowError) as exc:
        raise ValueError('non-canonical input') from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _integer(value: Any, lower: int, upper: int, name: str) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(name+' must be a bounded integer')
    return value


def _pose(value: Any) -> list[float]:
    if (not isinstance(value,list) or len(value)!=3 or
            any(type(x) not in (int,float) or not math.isfinite(x) or
                not -100<=x<=100 for x in value)):
        raise ValueError('pose must contain three finite coordinates within [-100,100]')
    return [float(x) for x in value]


def validate_fixture(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload,dict) or set(payload)!=ROOT_KEYS:
        raise ValueError('missing or unapproved fixture fields')
    fixed={'schema_version':'1.0.0','type':'MechaExercise','source_kind':'SYNTHETIC',
           'authority':'RESEARCH_ONLY','mode':'OFFLINE_ROBOTICS_DEMO','synthetic':True}
    for k,v in fixed.items():
        if type(payload[k]) is not type(v) or payload[k]!=v:
            raise ValueError('MECHA accepts synthetic research fixtures only: '+k)
    _integer(payload['seed'],0,(1<<32)-1,'seed')
    robot=payload['robot']
    if not isinstance(robot,dict) or set(robot)!=ROBOT_KEYS:
        raise ValueError('robot has missing or unauthorized fields')
    if not isinstance(robot['id'],str) or not NAME.fullmatch(robot['id']):
        raise ValueError('invalid synthetic rover id')
    if robot['class']!='INDUSTRIAL_INSPECTION_ROVER':
        raise ValueError('unsupported robot class')
    _pose(robot['pose'])
    _integer(robot['health_pct'],0,100,'health_pct')
    _integer(robot['power_budget_units'],1,1000000,'power_budget_units')
    env=payload['environment']
    if not isinstance(env,dict) or set(env)!=ENV_KEYS or env['terrain']!='SYNTHETIC_FLAT':
        raise ValueError('invalid synthetic environment')
    obstacles=env['obstacles']
    if not isinstance(obstacles,list) or len(obstacles)>50:
        raise ValueError('too many or malformed synthetic obstacles')
    for entry in obstacles:
        _pose(entry)
    assumptions=payload['assumptions']
    if (not isinstance(assumptions,list) or not 1<=len(assumptions)<=12 or
        any(not isinstance(v,str) or not ASCII_TEXT.fullmatch(v) for v in assumptions)):
        raise ValueError('unsafe assumption strings')
    if len(canonical_json(payload))>65536:
        raise ValueError('fixture exceeds 64 KiB')
    return json.loads(canonical_json(payload))
