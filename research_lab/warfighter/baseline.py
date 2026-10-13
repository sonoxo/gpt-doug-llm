"""Deterministic, nonforecasting synthetic aggregate exercises."""
from __future__ import annotations
from typing import Any
from .fixtures import validate_scenario


def run_baseline(scenario: dict[str,Any], *, what_if_delta: int=5) -> dict[str,Any]:
    data=validate_scenario(scenario)
    if type(what_if_delta) is not int or not 0<=what_if_delta<=20:
        raise ValueError('hypothetical change must be an integer 0..20')
    result={}
    for name,val in sorted(data['fixture'].items()):
        if name.endswith('_pct'):
            result[name]={'baseline':val,'hypothetical':min(100,val+what_if_delta),
                          'gap_to_100':100-val}
        else:
            result[name]={'synthetic_count':val}
    return {'engine':'synthetic-baseline-v1','authority':'RESEARCH_ONLY',
            'source_kind':'SYNTHETIC','synthetic':True,
            'interpretation':'hypothetical exercise, not forecast',
            'what_if_delta':what_if_delta,'metrics':result,
            'formula':'hypothetical=min(100,baseline+delta); gap_to_100=100-baseline'}
