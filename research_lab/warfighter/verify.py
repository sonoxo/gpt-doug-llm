"""Independent research replay; digest checks do not confer real-world authority."""
from __future__ import annotations
import hmac
from typing import Any
from .artifact import build_run, run_digest, source_hash
from .fixtures import digest


def verify_run(run:dict[str,Any]) -> dict[str,Any]:
    result={'status':'FAILED','run_sha256':'','method':'recompute_local_model_and_digests'}
    if not isinstance(run,dict):
        return result
    result['run_sha256']=str(run.get('run_sha256',''))[:64]
    try:
        if (run.get('authority')!='RESEARCH_ONLY' or run.get('synthetic') is not True or
                run.get('classification')!='SYNTHETIC' or run.get('source_kind')!='SYNTHETIC' or
                run.get('verification')!={'status':'PENDING','certificate_ref':None} or
                run.get('review')!={'status':'UNREVIEWED','review_record_ref':None} or
                run.get('publication')!={'status':'QUARANTINED','namespace':'warfighter_research'}):
            return result
        model=run['model']
        engine=model['id']
        if model['version']!='1.0.0' or not hmac.compare_digest(model['implementation_sha256'],source_hash(engine)):
            return result
        if not (hmac.compare_digest(run['input_sha256'],digest(run['input'])) and
                hmac.compare_digest(run['output_sha256'],digest(run['output'])) and
                hmac.compare_digest(run['run_sha256'],run_digest(run))):
            return result
        if engine=='baseline':
            from .baseline import run_baseline
            computed=run_baseline(run['input'])
            math_status='VERIFIED_FOR_MODEL'
        else:
            from .hilbert_adapter import analyze_math,verify_math
            computed=analyze_math(engine,run['input'])
            if not verify_math(engine,computed):
                return result
            math_status='INCONCLUSIVE' if computed.get('proof_status')=='INCONCLUSIVE' else 'VERIFIED_FOR_MODEL'
        if computed!=run['output']:
            return result
        rebuilt=build_run(run_id=run['id'],scenario=run['input'],engine=engine,
                          output=computed,code_sha256=source_hash(engine),generated_at=run['created_at'])
        if rebuilt!=run:
            return result
        result['status']=math_status
        return result
    except (ValueError,TypeError,KeyError,ImportError,OverflowError,FileNotFoundError,AttributeError):
        return result
