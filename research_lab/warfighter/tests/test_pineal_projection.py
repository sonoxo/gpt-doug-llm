import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from research_lab.warfighter.journal import ResearchJournal
from research_lab.warfighter.publication import publish_reviewed, revoke_finding
from research_lab.warfighter.pineal_projection import project_approved_finding, reconcile_pineal_projection
from research_lab.warfighter.verify import verify_run
from research_lab.warfighter.tests.test_verify import new_run

class FakePineal:
    rows=[]
    def __init__(self,db):
        self.db=db
    def put(self,**kwargs):
        if 'item_id' in kwargs:
            for row in self.rows:
                if row['id']==kwargs['item_id'] and row['version']==kwargs['expected_version']:
                    row['version']+=1
                    row.update({k:v for k,v in kwargs.items() if k not in ('expected_version','item_id')})
                    return dict(row)
            raise ValueError('Pineal optimistic update conflict')
        row={'id':str(len(self.rows)+1),'version':1,**kwargs}
        self.rows.append(row)
        return row

class TestPinealProjection(unittest.TestCase):
    def setUp(self):
        FakePineal.rows=[]
        module=types.ModuleType('pineal.store')
        module.PinealStore=FakePineal
        self.module=module

    def test_approved_opt_in_projection_idempotent_and_revocation(self):
        with patch.dict(sys.modules,{'pineal':types.ModuleType('pineal'),'pineal.store':self.module}):
            with tempfile.TemporaryDirectory() as d:
                db=Path(d)/'pineal.sqlite3'
                with ResearchJournal(Path(d)/'journal') as j:
                    r=new_run();j.record_run(r);j.record_verification(r['id'],verify_run(r))
                    j.record_review(r['id'],reviewer='demo-reviewer',decision='APPROVE',rationale='reviewed model',confirmed=True)
                    pub=publish_reviewed(j,r['id'])
                    self.assertFalse(db.exists())
                    a=project_approved_finding(j,pub['id'],pineal_db=db)
                    b=project_approved_finding(j,pub['id'],pineal_db=db)
                    self.assertEqual(a,b)
                    self.assertEqual(len(FakePineal.rows),1)
                    self.assertEqual(FakePineal.rows[0]['namespace'],'warfighter_research')
                    self.assertNotIn('operational_ready',FakePineal.rows[0]['value'])
                    revoke_finding(j,pub['id'],reason='superseded')
                    current=j._db.execute('SELECT state FROM projections WHERE publication_id=?',(pub['id'],)).fetchone()
                    self.assertEqual(current['state'],'STALE')
                    outcome=reconcile_pineal_projection(j,pub['id'],pineal_db=db)
                    self.assertEqual(outcome['state'],'REVOKED_PROJECTED')
                    self.assertIn('REVOKED',FakePineal.rows[0]['value'])

    def test_projection_rejects_unapproved_run(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'journal') as j:
                r=new_run();j.record_run(r)
                with self.assertRaises(ValueError):
                    project_approved_finding(j,'wr:publication:nonexistent',pineal_db=Path(d)/'not_created.db')
