"""Pure adapters for existing research_lab exact models (no task dispatch)."""
from __future__ import annotations
import importlib
from typing import Any

MODULES={'bio-hilbert':'research_lab.bio_hilbert', 'exact-linear':'research_lab.multidimensional'}


def _module(engine: str):
    if engine not in MODULES:
        raise ValueError('unsupported mathematical engine')
    return importlib.import_module(MODULES[engine])


def analyze_math(engine: str, problem: dict[str,Any]) -> dict[str,Any]:
    if not isinstance(problem,dict):
        raise ValueError('math input must be an object')
    if engine=='bio-hilbert':
        if type(problem.get('modes')) is not int or not 1 <= problem['modes'] <= 128:
            raise ValueError('bio-hilbert modes must be 1..128')
        if type(problem.get('steps')) is not int or not 0 <= problem['steps'] <= 8:
            raise ValueError('bio-hilbert steps must be 0..8')
    if engine=='exact-linear':
        rows=problem.get('matrix')
        if not isinstance(rows,list) or not 1<=len(rows)<=6:
            raise ValueError('exact-linear dimension must be 1..6')
    report=_module(engine).analyze(problem)
    proof = report.get('proof',{}).get('status','NOT_APPLICABLE') if engine=='exact-linear' else report.get('status','INCONCLUSIVE')
    return {'engine':engine,'authority':'RESEARCH_ONLY','classification':'SYNTHETIC',
            'synthetic':True,'model_scope':'mathematical_toy_model_only',
            'proof_status':proof,'report':report}


def verify_math(engine: str, report: dict[str,Any]) -> bool:
    if (not isinstance(report,dict) or report.get('engine')!=engine or
            report.get('authority')!='RESEARCH_ONLY' or report.get('synthetic') is not True or
            report.get('model_scope')!='mathematical_toy_model_only'):
        return False
    try:
        raw=report['report']
        proof=raw.get('proof',{}).get('status','NOT_APPLICABLE') if engine=='exact-linear' else raw.get('status','INCONCLUSIVE')
        return proof==report.get('proof_status') and bool(_module(engine).verify(raw))
    except (ImportError,KeyError,ValueError,TypeError,OverflowError):
        return False
