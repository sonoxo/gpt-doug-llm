import copy
import tempfile
import unittest
from pathlib import Path
from research_lab.warfighter.journal import ResearchJournal
from research_lab.warfighter.verify import verify_run
from research_lab.warfighter.tests.test_verify import new_run

class TestJournal(unittest.TestCase):
    def test_unverified_and_unconfirmed_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as d:
            j=ResearchJournal(Path(d)/'journal')
            r=new_run(); j.record_run(r)
            with self.assertRaises(ValueError):
                j.record_review(r['id'],reviewer='tester',decision='APPROVE',rationale='checked',confirmed=True)
            j.record_verification(r['id'],verify_run(r))
            with self.assertRaises(ValueError):
                j.record_review(r['id'],reviewer='tester',decision='APPROVE',rationale='checked',confirmed=False)
            approved=j.record_review(r['id'],reviewer='tester',decision='APPROVE',rationale='checked',confirmed=True)
            self.assertEqual(approved['decision'],'APPROVE')
            self.assertEqual(approved['run_digest'],r['run_sha256'])
            self.assertTrue(j.verify_audit()['ok'])
            j.close()

    def test_spoofed_review_field_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as d:
            j=ResearchJournal(Path(d)/'journal')
            r=new_run()
            r['review']['status']='APPROVED'
            with self.assertRaises(ValueError):
                j.record_run(r)
            j.close()

    def test_duplicate_artifact_conflicts_only_on_change(self):
        with tempfile.TemporaryDirectory() as d:
            j=ResearchJournal(Path(d)/'journal')
            r=new_run()
            j.record_run(r)
            j.record_run(r)
            tampered=copy.deepcopy(r)
            tampered['output']['what_if_delta']=7
            with self.assertRaises(ValueError):
                j.record_run(tampered)
            j.close()

    def test_outside_symlink_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; a.mkdir()
            link=Path(d)/'link'; link.symlink_to(a)
            with self.assertRaises(ValueError):
                ResearchJournal(link)

    def test_replay_check_before_approval_detects_code_change(self):
        with tempfile.TemporaryDirectory() as d:
            j=ResearchJournal(Path(d)/'journal')
            r=new_run()
            j.record_run(r)
            result=verify_run(r)
            j.record_verification(r['id'],result)
            j._db.execute("UPDATE runs SET content = ? WHERE id = ?",('{}',r['id']))
            j._db.commit()
            with self.assertRaises(ValueError):
                j.record_review(r['id'],reviewer='tester',decision='APPROVE',rationale='checked',confirmed=True)
            j.close()
