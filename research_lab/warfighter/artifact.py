"""Immutable-like research run envelopes, never trusted without replay."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from .fixtures import canonical_json, digest

ENGINE_FILES={'baseline':'warfighter/baseline.py',
              'bio-hilbert':'bio_hilbert.py',
              'exact-linear':'multidimensional.py'}
ROOT=Path(__file__).resolve().parents[1]
HEX=re.compile(r'[0-9a-f]{64}\Z')
RUN_ID=re.compile(r'wr:run:[a-zA-Z0-9._-]{1,80}\Z')


def source_hash(engine: str) -> str:
    if engine not in ENGINE_FILES:
        raise ValueError('unknown research engine')
    target=(ROOT/ENGINE_FILES[engine]).resolve(strict=True)
    if not target.is_file() or not target.is_relative_to(ROOT):
        raise ValueError('invalid research engine source')
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _time(stamp: str) -> None:
    try:
        parsed=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timezone required')
    except (TypeError,ValueError,AttributeError) as exc:
        raise ValueError('timestamp must be ISO8601 with timezone') from exc


def run_digest(run: dict[str,Any]) -> str:
    return digest({k:v for k,v in run.items() if k!='run_sha256'})


def build_run(*,run_id:str,scenario:dict[str,Any],engine:str,output:dict[str,Any],
              code_sha256:str,generated_at:str) -> dict[str,Any]:
    if not isinstance(run_id,str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('invalid namespaced run ID')
    _time(generated_at)
    if not isinstance(scenario,dict) or not isinstance(output,dict):
        raise ValueError('input/output must be JSON objects')
    if not isinstance(code_sha256,str) or not HEX.fullmatch(code_sha256) or source_hash(engine)!=code_sha256:
        raise ValueError('code hash not verified against local engine')
    if engine=='baseline':
        from .fixtures import validate_scenario
        scenario=validate_scenario(scenario)
    envelope={
        'schema_version':'1.0.0','id':run_id,'type':'SimulationRun',
        'classification':'SYNTHETIC','source_kind':'SYNTHETIC','synthetic':True,
        'authority':'RESEARCH_ONLY','created_at':generated_at,
        'source_refs':['synthetic:local-user-fixture'],
        'scope':'specified mathematical model; no operational conclusions',
        'scenario_ref':str(scenario.get('scenario_id',run_id)),
        'model':{'id':engine,'version':'1.0.0','implementation_sha256':code_sha256},
        'input':scenario,'output':output,'input_sha256':digest(scenario),'output_sha256':digest(output),
        'verification':{'status':'PENDING','certificate_ref':None},
        'review':{'status':'UNREVIEWED','review_record_ref':None},
        'publication':{'status':'QUARANTINED','namespace':'warfighter_research'},
    }
    envelope['run_sha256']=run_digest(envelope)
    if len(canonical_json(envelope))>1048576:
        raise ValueError('run artifact exceeds 1MiB')
    return envelope
