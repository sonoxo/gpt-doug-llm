"""Explicit manual PINEAL research-only projection; no implicit synchronization."""
from __future__ import annotations
import importlib
from pathlib import Path
from typing import Any
from .fixtures import canonical_json
from .journal import ResearchJournal
from .publication import list_findings


def _current(journal:ResearchJournal,publication_id:str)->dict[str,Any]:
    for row in list_findings(journal,approved_only=False):
        if row['id']==publication_id:
            return row
    raise ValueError('unknown reviewed research publication')


def _db(pineal_db:Path):
    path=Path(pineal_db).expanduser()
    if path.is_symlink():
        raise ValueError('PINEAL database symlink prohibited')
    cls=importlib.import_module('pineal.store').PinealStore
    return cls(path)


def _save(journal,publication_id,*,pineal_id,pineal_version,last_digest,state):
    with journal._db:
        journal._db.execute('BEGIN IMMEDIATE')
        journal._db.execute('''INSERT INTO projections(publication_id,pineal_id,pineal_version,last_digest,state)
          VALUES(?,?,?,?,?) ON CONFLICT(publication_id) DO UPDATE SET
          pineal_id=excluded.pineal_id,pineal_version=excluded.pineal_version,
          last_digest=excluded.last_digest,state=excluded.state''',
            (publication_id,pineal_id,pineal_version,last_digest,state))
        journal._event('PINEAL_PROJECTION',publication_id,{'state':state,'digest':last_digest})


def _project(journal:ResearchJournal,publication_id:str,*,pineal_db:Path,allow_revoked:bool)->dict[str,Any]:
    pub=_current(journal,publication_id)
    status=pub['status']
    if status=='REVOKED' and not allow_revoked:
        raise ValueError('revoked research findings cannot be newly projected')
    if status not in {'PUBLISHED_RESEARCH_ONLY','REVOKED'}:
        raise ValueError('research finding is not approved')
    prior=journal._db.execute('SELECT * FROM projections WHERE publication_id=?',(publication_id,)).fetchone()
    if prior and prior['state']=='SYNCED' and prior['last_digest']==pub['run_sha256'] and status=='PUBLISHED_RESEARCH_ONLY':
        return {'publication_id':publication_id,'state':'SYNCED','pineal_id':prior['pineal_id'],
                'authority':'RESEARCH_ONLY'}
    if status=='REVOKED' and not prior:
        return {'publication_id':publication_id,'state':'NOT_PROJECTED','authority':'RESEARCH_ONLY'}
    value=canonical_json({'publication_id':publication_id,'run_digest':pub['run_sha256'],
             'status':status,'scope':'synthetic mathematically reviewed research only',
             'no_operational_authority':True}).decode('ascii')
    try:
        store=_db(pineal_db)
        kwargs={'namespace':'warfighter_research','subject':publication_id,
                'predicate':'research_publication_status','value':value,
                'source':'explicit-local-human-reviewed-research','confidence':0.5}
        if prior and prior['pineal_id']:
            kwargs.update(item_id=prior['pineal_id'],expected_version=prior['pineal_version'])
        new=store.put(**kwargs)
    except (ImportError,ValueError,OSError,PermissionError,LookupError) as exc:
        _save(journal,publication_id,pineal_id=prior['pineal_id'] if prior else None,
              pineal_version=prior['pineal_version'] if prior else None,
              last_digest=pub['run_sha256'],state='PARTIALLY_PROJECTED')
        return {'publication_id':publication_id,'state':'PARTIALLY_PROJECTED','error':str(exc)[:120],
                'authority':'RESEARCH_ONLY'}
    result_state='REVOKED_PROJECTED' if status=='REVOKED' else 'SYNCED'
    _save(journal,publication_id,pineal_id=str(new['id']),pineal_version=int(new['version']),
          last_digest=pub['run_sha256'],state=result_state)
    return {'publication_id':publication_id,'state':result_state,'pineal_id':str(new['id']),
            'authority':'RESEARCH_ONLY'}


def project_approved_finding(journal:ResearchJournal,publication_id:str,*,pineal_db:Path)->dict[str,Any]:
    return _project(journal,publication_id,pineal_db=pineal_db,allow_revoked=False)


def reconcile_pineal_projection(journal:ResearchJournal,publication_id:str,*,pineal_db:Path)->dict[str,Any]:
    return _project(journal,publication_id,pineal_db=pineal_db,allow_revoked=True)
