"""Local-only SQLite journal for synthetic research and operator-labeled reviews.

Hash chains are tamper-evident only with an independently trusted head.
Review labels are not authenticated human identities or operational grants.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from .fixtures import canonical_json,digest
from .verify import verify_run


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _label(value: Any, title: str, cap: int=256) -> str:
    if not isinstance(value,str) or not value.strip() or len(value)>cap or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('invalid '+title)
    return value.strip()


class ResearchJournal:
    def __init__(self, workspace: Path):
        self.workspace=Path(workspace).expanduser()
        if self.workspace.is_symlink():
            raise ValueError('symlink workspaces prohibited')
        if self.workspace.exists() and not self.workspace.is_dir():
            raise ValueError('workspace must be a directory')
        self.workspace.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.workspace.is_symlink():
            raise ValueError('workspace must not be symlink')
        self.workspace.chmod(0o700)
        self.path=self.workspace/'research.sqlite3'
        if self.path.is_symlink():
            raise ValueError('journal file must not be symlink')
        if not self.path.exists():
            fd=os.open(str(self.path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.close(fd)
        self._db=sqlite3.connect(str(self.path),timeout=10)
        self._db.row_factory=sqlite3.Row
        self._db.execute('PRAGMA busy_timeout=10000')
        self._db.execute('PRAGMA foreign_keys=ON')
        self._db.executescript('''
        CREATE TABLE IF NOT EXISTS runs(
          id TEXT PRIMARY KEY, content TEXT NOT NULL, digest TEXT NOT NULL,
          verified TEXT NOT NULL DEFAULT 'PENDING', verify_digest TEXT
        );
        CREATE TABLE IF NOT EXISTS reviews(
          id TEXT PRIMARY KEY, run_id TEXT NOT NULL,run_digest TEXT NOT NULL,
          decision TEXT NOT NULL, reviewer TEXT NOT NULL,rationale TEXT NOT NULL,
          stamp TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES runs(id)
        );
        CREATE TABLE IF NOT EXISTS publications(
          id TEXT PRIMARY KEY,run_id TEXT NOT NULL UNIQUE,run_digest TEXT NOT NULL,
          review_id TEXT NOT NULL,status TEXT NOT NULL,stamp TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES runs(id),FOREIGN KEY(review_id) REFERENCES reviews(id)
        );
        CREATE TABLE IF NOT EXISTS projections(
          publication_id TEXT PRIMARY KEY, pineal_id TEXT, pineal_version INTEGER,
          state TEXT NOT NULL, last_digest TEXT,FOREIGN KEY(publication_id) REFERENCES publications(id)
        );
        CREATE TABLE IF NOT EXISTS events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT,stamp TEXT NOT NULL,action TEXT NOT NULL,
          entity TEXT NOT NULL,detail TEXT NOT NULL,prev TEXT NOT NULL,hash TEXT NOT NULL
        );
        ''')
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self,exc_type,exc,tb):
        self.close()

    def _event(self,action:str,entity:str,detail:dict[str,Any]) -> None:
        prev=self._db.execute('SELECT hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        parent=prev['hash'] if prev else '0'*64
        stamp=_now()
        text=canonical_json(detail).decode('ascii')
        encoded=canonical_json([stamp,action,entity,text,parent])
        self._db.execute('INSERT INTO events(stamp,action,entity,detail,prev,hash) VALUES(?,?,?,?,?,?)',
                        (stamp,action,entity,text,parent,hashlib.sha256(encoded).hexdigest()))

    def verify_audit(self) -> dict[str,Any]:
        parent='0'*64
        count=0
        for row in self._db.execute('SELECT * FROM events ORDER BY seq').fetchall():
            expected=hashlib.sha256(canonical_json([row['stamp'],row['action'],row['entity'],row['detail'],parent])).hexdigest()
            if row['prev']!=parent or row['hash']!=expected:
                return {'ok':False,'checked':count,'failure_seq':row['seq']}
            parent=row['hash'];count+=1
        return {'ok':True,'checked':count,'head':parent}

    def record_run(self,run:dict[str,Any]) -> str:
        verified=verify_run(run)
        if verified['status']=='FAILED':
            raise ValueError('cannot admit malformed or tampered run artifact')
        body=canonical_json(run)
        if len(body)>1048576:
            raise ValueError('research artifact exceeds size cap')
        run_id=run['id'];sha=run['run_sha256']
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            old=self._db.execute('SELECT digest,content FROM runs WHERE id=?',(run_id,)).fetchone()
            if old:
                if old['digest']!=sha or old['content']!=body.decode('ascii'):
                    raise ValueError('run id conflicts with existing digest')
                return run_id
            self._db.execute('INSERT INTO runs(id,content,digest) VALUES(?,?,?)',
                             (run_id,body.decode('ascii'),sha))
            self._event('RUN_QUARANTINED',run_id,{'run_sha256':sha,'authority':'RESEARCH_ONLY'})
        return run_id

    def get_run(self,run_id:str) -> dict[str,Any]:
        row=self._db.execute('SELECT content FROM runs WHERE id=?',(run_id,)).fetchone()
        if row is None:
            raise ValueError('unknown research run')
        return json.loads(row['content'])

    def record_verification(self,run_id:str,result:dict[str,Any]) -> None:
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            run=self.get_run(run_id)
            verified=verify_run(run)
            if verified['status']=='FAILED' or verified!=result:
                raise ValueError('verification must be fresh and reproducible')
            self._db.execute('UPDATE runs SET verified=?,verify_digest=? WHERE id=?',
                             (verified['status'],run['run_sha256'],run_id))
            self._event('RUN_VERIFIED',run_id,{'status':verified['status'],'digest':run['run_sha256']})

    def record_review(self,run_id:str, *, reviewer:str,decision:str,rationale:str,confirmed:bool) -> dict[str,Any]:
        _label(reviewer,'reviewer',80);_label(rationale,'rationale',1024)
        if decision not in {'APPROVE','REJECT'} or confirmed is not True:
            raise ValueError('explicit operator confirmation and legal decision required')
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            run=self.get_run(run_id)
            vr=verify_run(run)
            stored=self._db.execute('SELECT digest,verified,verify_digest FROM runs WHERE id=?',(run_id,)).fetchone()
            if (vr['status']!='VERIFIED_FOR_MODEL' or stored['verified']!='VERIFIED_FOR_MODEL'
                    or stored['digest']!=run['run_sha256'] or stored['verify_digest']!=run['run_sha256']):
                raise ValueError('run has no current model verification')
            other=self._db.execute('SELECT * FROM reviews WHERE run_id=?',(run_id,)).fetchone()
            if other:
                raise ValueError('review already exists; new version required')
            stamp=_now();ref='wr:review:'+hashlib.sha256(canonical_json([run_id,run['run_sha256'],reviewer,decision,stamp])).hexdigest()[:24]
            self._db.execute('INSERT INTO reviews(id,run_id,run_digest,decision,reviewer,rationale,stamp) VALUES(?,?,?,?,?,?,?)',
                             (ref,run_id,run['run_sha256'],decision,reviewer,rationale,stamp))
            self._event('HUMAN_REVIEW',run_id,{'review_ref':ref,'decision':decision,'run_sha256':run['run_sha256']})
            return {'id':ref,'decision':decision,'run_id':run_id,'run_digest':run['run_sha256'],
                    'reviewer_label':reviewer,'stamp':stamp,'authority':'RESEARCH_ONLY'}
