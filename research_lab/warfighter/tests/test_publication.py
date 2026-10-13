import tempfile
import unittest
from pathlib import Path
from research_lab.warfighter.journal import ResearchJournal
from research_lab.warfighter.publication import publish_reviewed, revoke_finding, list_findings
from research_lab.warfighter.verify import verify_run
from research_lab.warfighter.tests.test_verify import new_run

class TestPublication(unittest.TestCase):
    def test_unreviewed_never_published(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'db') as j:
                r=new_run();j.record_run(r)
                with self.assertRaises(ValueError):
                    publish_reviewed(j,r['id'])
                self.assertEqual(list_findings(j),[])

    def test_approved_research_only_and_revocation(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'db') as j:
                r=new_run();j.record_run(r);j.record_verification(r['id'],verify_run(r))
                rev=j.record_review(r['id'],reviewer='human-operator-label',decision='APPROVE',
                                    rationale='toy model math replay',confirmed=True)
                first=publish_reviewed(j,r['id'])
                again=publish_reviewed(j,r['id'])
                self.assertEqual(first,again)
                self.assertEqual(first['authority'],'RESEARCH_ONLY')
                self.assertEqual(first['status'],'PUBLISHED_RESEARCH_ONLY')
                self.assertEqual(len(list_findings(j)),1)
                revoked=revoke_finding(j,first['id'],reason='superseded model')
                self.assertEqual(revoked['status'],'REVOKED')
                self.assertEqual(list_findings(j),[])
                self.assertEqual(len(list_findings(j,approved_only=False)),1)
                with self.assertRaises(ValueError):
                    publish_reviewed(j,r['id'])
                self.assertTrue(j.verify_audit()['ok'])

    def test_tampered_journal_run_cannot_be_republished_or_queried(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'db') as j:
                r=new_run(); j.record_run(r); j.record_verification(r['id'],verify_run(r))
                j.record_review(r['id'],reviewer='operator',decision='APPROVE',
                                rationale='math checked',confirmed=True)
                publish_reviewed(j,r['id'])
                j._db.execute("UPDATE runs SET content='{}' WHERE id=?",(r['id'],))
                j._db.commit()
                with self.assertRaises(ValueError):
                    list_findings(j)
                with self.assertRaises(ValueError):
                    publish_reviewed(j,r['id'])

    def test_modified_review_decision_cannot_manufacture_approval(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'db') as j:
                r=new_run();j.record_run(r);j.record_verification(r['id'],verify_run(r))
                j.record_review(r['id'],reviewer='operator',decision='REJECT',
                                rationale='not publishable',confirmed=True)
                j._db.execute("UPDATE reviews SET decision='APPROVE' WHERE run_id=?",(r['id'],))
                j._db.commit()
                with self.assertRaises(ValueError):
                    publish_reviewed(j,r['id'])

    def test_rejected_cannot_publish(self):
        with tempfile.TemporaryDirectory() as d:
            with ResearchJournal(Path(d)/'db') as j:
                r=new_run();j.record_run(r);j.record_verification(r['id'],verify_run(r))
                j.record_review(r['id'],reviewer='local-human-label',decision='REJECT',
                                rationale='not approved',confirmed=True)
                with self.assertRaises(ValueError):
                    publish_reviewed(j,r['id'])
