"""Explicit human-approved, synthetic-only research overlay and revocation."""
from __future__ import annotations
import hashlib
import json
from typing import Any
from .fixtures import canonical_json
from .verify import verify_run
from .journal import ResearchJournal, _label, _now


def _row(row):
    return {'id':row['id'],'run_id':row['run_id'],
            'run_sha256':row['run_digest'],'review_ref':row['review_id'],
            'status':row['status'],'stamp':row['stamp'],
            'authority':'RESEARCH_ONLY','namespace':'warfighter_research'}


def _has_review_event(journal: ResearchJournal, *, run_id: str,
                      review_id: str, run_digest: str) -> bool:
    events=journal._db.execute(
        "SELECT detail FROM events WHERE action='HUMAN_REVIEW' AND entity=?",(run_id,)
    ).fetchall()
    for event in events:
        detail=json.loads(event['detail'])
        if (detail.get('review_ref')==review_id and detail.get('decision')=='APPROVE'
                and detail.get('run_sha256')==run_digest):
            return True
    return False


def _assert_integrity(journal: ResearchJournal, row) -> None:
    run=journal.get_run(row['run_id'])
    if (verify_run(run)['status']!='VERIFIED_FOR_MODEL' or
            run.get('run_sha256') != row['run_digest']):
        raise ValueError('published run has lost mathematical integrity')
    stored=journal._db.execute('SELECT digest,verified,verify_digest FROM runs WHERE id=?',(row['run_id'],)).fetchone()
    review=journal._db.execute('SELECT * FROM reviews WHERE id=?',(row['review_id'],)).fetchone()
    if (stored is None or stored['digest'] != row['run_digest'] or
            stored['verified']!='VERIFIED_FOR_MODEL' or stored['verify_digest'] != row['run_digest'] or
            review is None or review['run_digest'] != row['run_digest'] or review['decision']!='APPROVE'):
        raise ValueError('published research approval/digest binding failed')
    if not _has_review_event(journal,run_id=row['run_id'],review_id=row['review_id'],
                             run_digest=row['run_digest']):
        raise ValueError('matching human-review event not present')


def publish_reviewed(journal: ResearchJournal, run_id: str) -> dict[str,Any]:
    if not journal.verify_audit()['ok']:
        raise ValueError('audit chain validation failed')
    db=journal._db
    with db:
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT * FROM publications WHERE run_id=?',(run_id,)).fetchone()
        if prior:
            _assert_integrity(journal,prior)
            if prior['status']=='REVOKED':
                raise ValueError('revoked publication requires new research run')
            return _row(prior)
        run=journal.get_run(run_id)
        verified=verify_run(run)
        if verified['status']!='VERIFIED_FOR_MODEL':
            raise ValueError('unverified research cannot publish')
        source=db.execute('SELECT digest,verified,verify_digest FROM runs WHERE id=?',(run_id,)).fetchone()
        if (source['digest']!=run['run_sha256'] or source['verify_digest']!=run['run_sha256']
                or source['verified']!='VERIFIED_FOR_MODEL'):
            raise ValueError('stored run verification mismatch')
        review=db.execute('SELECT * FROM reviews WHERE run_id=?',(run_id,)).fetchone()
        if review is None or review['decision']!='APPROVE' or review['run_digest']!=run['run_sha256']:
            raise ValueError('human research approval required')
        if not _has_review_event(journal,run_id=run_id,review_id=review['id'],run_digest=run['run_sha256']):
            raise ValueError('matching audited approval event required')
        pub_id='wr:publication:'+hashlib.sha256(canonical_json([run_id,run['run_sha256'],review['id']])).hexdigest()[:24]
        stamp=_now()
        db.execute('INSERT INTO publications(id,run_id,run_digest,review_id,status,stamp) VALUES(?,?,?,?,?,?)',
                   (pub_id,run_id,run['run_sha256'],review['id'],'PUBLISHED_RESEARCH_ONLY',stamp))
        journal._event('PUBLISHED_RESEARCH_ONLY',pub_id,{'run_id':run_id,'review_id':review['id'],'run_sha256':run['run_sha256']})
        return _row(db.execute('SELECT * FROM publications WHERE id=?',(pub_id,)).fetchone())


def revoke_finding(journal:ResearchJournal,publication_id:str,*,reason:str)->dict[str,Any]:
    _label(reason,'revocation reason',1024)
    with journal._db:
        journal._db.execute('BEGIN IMMEDIATE')
        row=journal._db.execute('SELECT * FROM publications WHERE id=?',(publication_id,)).fetchone()
        if row is None:
            raise ValueError('publication id not found')
        if row['status']!='REVOKED':
            journal._db.execute("UPDATE publications SET status='REVOKED' WHERE id=?",(publication_id,))
            journal._event('RESEARCH_REVOKED',publication_id,{'reason':reason,'original_digest':row['run_digest']})
            journal._db.execute("UPDATE projections SET state='STALE' WHERE publication_id=?",(publication_id,))
        return _row(journal._db.execute('SELECT * FROM publications WHERE id=?',(publication_id,)).fetchone())


def list_findings(journal:ResearchJournal,*,approved_only:bool=True)->list[dict[str,Any]]:
    if not journal.verify_audit()['ok']:
        raise ValueError('audit chain validation failed')
    query='SELECT * FROM publications'
    if approved_only:
        query+=" WHERE status='PUBLISHED_RESEARCH_ONLY'"
    query+=' ORDER BY stamp DESC,id ASC LIMIT 100'
    rows=journal._db.execute(query).fetchall()
    for row in rows:
        _assert_integrity(journal,row)
    return [_row(row) for row in rows]
