"""End-to-end research-only projection through the *real* PINEAL SQLite store."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from research_lab.warfighter.journal import ResearchJournal
from research_lab.warfighter.publication import publish_reviewed, revoke_finding
from research_lab.warfighter.pineal_projection import (
    project_approved_finding, reconcile_pineal_projection,
)
from research_lab.warfighter.tests.test_verify import new_run
from research_lab.warfighter.verify import verify_run

try:
    from pineal.store import PinealStore
except ImportError:
    PinealStore = None


@unittest.skipIf(PinealStore is None, 'full PINEAL package not installed on local-only fixture')
class TestRealPineal(unittest.TestCase):
    def test_verified_research_projection_revocation_audited(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pineal_db = root / 'memory.sqlite3'
            with ResearchJournal(root / 'research') as journal:
                run = new_run()
                journal.record_run(run)
                journal.record_verification(run['id'], verify_run(run))
                journal.record_review(
                    run['id'], reviewer='local-test-reviewer', decision='APPROVE',
                    rationale='verified synthetic research', confirmed=True)
                published = publish_reviewed(journal, run['id'])
                self.assertFalse(pineal_db.exists())
                projected = project_approved_finding(
                    journal, published['id'], pineal_db=pineal_db)
                self.assertEqual(projected['state'], 'SYNCED')
                store = PinealStore(pineal_db)
                row = store.get(projected['pineal_id'])
                self.assertEqual(row['namespace'], 'warfighter_research')
                self.assertEqual(json.loads(row['value'])['status'], 'PUBLISHED_RESEARCH_ONLY')
                self.assertTrue(store.verify_audit()['ok'])
                self.assertEqual(store.verify_audit()['checked'], 1)

                revoke_finding(journal, published['id'], reason='end-of-exercise')
                revoked = reconcile_pineal_projection(
                    journal, published['id'], pineal_db=pineal_db)
                self.assertEqual(revoked['state'], 'REVOKED_PROJECTED')
                new = store.get(projected['pineal_id'])
                self.assertEqual(json.loads(new['value'])['status'], 'REVOKED')
                self.assertEqual(new['version'], 2)
                self.assertTrue(store.verify_audit()['ok'])
                self.assertEqual(store.verify_audit()['checked'], 2)
                self.assertTrue(journal.verify_audit()['ok'])


if __name__ == '__main__':
    unittest.main()
