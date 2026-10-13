"""Offline, human-controlled Warfighter research CLI.

No network, XQE dispatch or operational authority. Approval requires a TTY
with an exact artifact-digest confirmation and grants research publication only.
"""
from __future__ import annotations
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .artifact import build_run, source_hash
from .baseline import run_baseline
from .fixtures import load_scenario
from .hilbert_adapter import analyze_math
from .journal import ResearchJournal
from .publication import publish_reviewed, revoke_finding, list_findings
from .schema import load_schema
from .verify import verify_run


def _parser():
    p=argparse.ArgumentParser(prog='gpt-doug warfighter',description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('status','doctor','ontology','scenario','simulate','verify','review',
                 'publish','findings','revoke','pineal-project'):
        cmd=sub.add_parser(name)
        if name not in {'doctor','ontology'}:
            cmd.add_argument('--workspace',type=Path)
        if name=='ontology':
            cmd.add_argument('--validate',action='store_true')
        if name=='scenario':
            cmd.add_argument('action',choices=('validate',))
        if name in {'scenario','simulate'}:
            cmd.add_argument('file',type=Path)
            cmd.add_argument('--input-root',type=Path,required=True)
        if name=='simulate':
            cmd.add_argument('--engine',choices=('baseline','bio-hilbert','exact-linear'),default='baseline')
        if name in {'verify','review','publish'}:
            cmd.add_argument('run_id')
        if name=='review':
            cmd.add_argument('--decision',choices=('approve','reject'),required=True)
            cmd.add_argument('--reviewer',required=True)
            cmd.add_argument('--rationale',required=True)
        if name=='revoke':
            cmd.add_argument('publication_id')
            cmd.add_argument('--reason',required=True)
        if name=='pineal-project':
            cmd.add_argument('publication_id')
            cmd.add_argument('--pineal-db',type=Path,required=True)
    return p


def _read_math(path:Path,root:Path):
    if path.is_symlink():
        raise ValueError('symlink inputs prohibited')
    try:
        actual=path.resolve(strict=True)
        origin=root.resolve(strict=True)
    except OSError as exc:
        raise ValueError('input not found') from exc
    if not actual.is_relative_to(origin) or actual.stat().st_size>65536:
        raise ValueError('input outside root or exceeds 64 KiB')
    try:
        obj=json.loads(actual.read_text(encoding='utf-8'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite math input')))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('invalid math JSON') from exc
    if not isinstance(obj,dict):
        raise ValueError('math input must be object')
    return obj


def _workspace(args):
    if args.workspace is None:
        raise ValueError('explicit --workspace required for this action')
    return ResearchJournal(args.workspace)


def _run(args):
    if args.cmd=='status':
        return {'system':'GPT-Doug Warfighter Research Core','authority':'RESEARCH_ONLY',
                'classification':'SYNTHETIC','operational_connected':False,
                'external_calls':0,'workspace_configured':bool(args.workspace)}
    if args.cmd=='doctor':
        schema=load_schema()
        return {'status':'RESEARCH_ONLY','ontology':schema['ontology_id'],
                'object_types':len(schema['object_types']),
                'edge_types':len(schema['edge_types']),
                'synthetic_only':True,'external_calls':0,
                'automatic_publication':False,'military_authority':False}
    if args.cmd=='ontology':
        schema=load_schema()
        return {'status':'VALIDATED' if args.validate else 'RESEARCH_ONLY',
                'ontology':schema['ontology_id'],'authority':schema['authority'],
                'object_types':len(schema['object_types']),'edge_types':len(schema['edge_types'])}
    if args.cmd=='scenario':
        scenario=load_scenario(args.file,allowed_root=args.input_root)
        return {'status':'VALID_SYNTHETIC_SCENARIO','scenario_id':scenario['scenario_id'],
                'authority':'RESEARCH_ONLY'}
    if args.cmd=='simulate':
        if args.engine=='baseline':
            inp=load_scenario(args.file,allowed_root=args.input_root)
            out=run_baseline(inp)
        else:
            inp=_read_math(args.file,args.input_root)
            out=analyze_math(args.engine,inp)
        run=build_run(run_id='wr:run:'+uuid.uuid4().hex[:24],scenario=inp,engine=args.engine,
                      output=out,code_sha256=source_hash(args.engine),
                      generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        with _workspace(args) as journal:
            journal.record_run(run)
        return {'status':'QUARANTINED','run_id':run['id'],'run_sha256':run['run_sha256'],
                'engine':args.engine,'authority':'RESEARCH_ONLY','synthetic':True,
                'external_calls':0}
    if args.cmd=='verify':
        with _workspace(args) as journal:
            run=journal.get_run(args.run_id)
            result=verify_run(run)
            if result['status']=='FAILED':
                return result
            journal.record_verification(args.run_id,result)
            return result
    if args.cmd=='review':
        if not sys.stdin.isatty():
            raise PermissionError('research approval requires an interactive local terminal')
        with _workspace(args) as journal:
            run=journal.get_run(args.run_id)
            stamp=run['run_sha256']
            confirmation=input('Confirm exact research digest '+stamp+' > ').strip()
            if confirmation!=stamp:
                raise PermissionError('review digest confirmation did not match')
            return journal.record_review(args.run_id,reviewer=args.reviewer,
                        decision=args.decision.upper(),rationale=args.rationale,confirmed=True)
    if args.cmd=='publish':
        with _workspace(args) as journal:
            return publish_reviewed(journal,args.run_id)
    if args.cmd=='findings':
        with _workspace(args) as journal:
            return {'authority':'RESEARCH_ONLY','findings':list_findings(journal)}
    if args.cmd=='revoke':
        with _workspace(args) as journal:
            return revoke_finding(journal,args.publication_id,reason=args.reason)
    if args.cmd=='pineal-project':
        from .pineal_projection import project_approved_finding
        with _workspace(args) as journal:
            return project_approved_finding(journal,args.publication_id,pineal_db=args.pineal_db)
    raise ValueError('unknown command')


def main(argv:list[str]|None=None)->int:
    try:
        args=_parser().parse_args(argv)
        data=_run(args)
        if data.get('status')=='FAILED':
            print(json.dumps(data,sort_keys=True,indent=2))
            return 3
        print(json.dumps(data,sort_keys=True,indent=2))
        return 0
    except PermissionError as exc:
        print(json.dumps({'ok':False,'error':str(exc)}),file=sys.stderr)
        return 4
    except (ValueError,OSError,TypeError,KeyError,ImportError,OverflowError) as exc:
        msg=str(exc)
        print(json.dumps({'ok':False,'error':msg[:200],'type':type(exc).__name__}),file=sys.stderr)
        return 4 if ('approval' in msg or 'unverified research' in msg or 'human research' in msg or 'verification mismatch' in msg) else 2

if __name__=='__main__':
    raise SystemExit(main())
