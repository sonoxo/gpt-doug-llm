import json
import tempfile
import unittest
from pathlib import Path

from sonoxo_fleet import si_readiness as si
from sonoxo_fleet.cli import SNAPSHOT, load_snapshot

class SIReadinessTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_snapshot(SNAPSHOT)

    def test_offline(self):
        r=si.build_report(self.snapshot)
        self.assertEqual(r["repository_count"],206)
        self.assertEqual(r["counts"]["not_scanned"],206)
        self.assertFalse(r["policy"]["remote_writes"])

    def test_advisory_detection(self):
        data=json.dumps({"packages":{"node_modules/proxy-addr":{"version":"2.0.7"},"node_modules/source-map-js":{"version":"1.2.1"}}})
        r=si.audit_npm_lock(data)
        self.assertEqual(len(r["findings"]),2)
        patched=json.dumps({"packages":{"node_modules/proxy-addr":{"version":"2.0.8"},"node_modules/source-map-js":{"version":"1.2.2"}}})
        self.assertEqual(si.audit_npm_lock(patched)["findings"],[])

    def test_review_scope(self):
        calls=[]
        def fetch(repo,branch,path):
            calls.append(path)
            return None
        r=si.build_report(self.snapshot,limit=1,fetch_text=fetch)
        self.assertEqual(r["manifest_inspections"],1)
        self.assertEqual(len(calls),3)
        self.assertEqual(r["counts"]["review_current_evidence"],1)

    def test_errors_fail_closed(self):
        with self.assertRaises(si.AuditError):
            si.audit_npm_lock("broken")
        with self.assertRaises(si.AuditError):
            si.build_report(self.snapshot,limit=207)
        with self.assertRaises(si.AuditError):
            si.github_public_text("other/repo","main","package-lock.json")
        def bad(*args):
            raise RuntimeError("secret in token")
        report=si.build_report(self.snapshot,limit=1,fetch_text=bad)
        self.assertEqual(report["counts"]["incomplete_evidence"],1)
        self.assertNotIn("secret in token",json.dumps(report))
        self.assertFalse(report["policy"]["secret_collection"])

    def test_local_output_only(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(si.main(["--output",td]),0)
            self.assertTrue((Path(td)/"si-readiness.json").is_file())
            self.assertEqual(si.main(["--output",td]),2)
            self.assertEqual(si.main(["--output",td,"--force"]),0)

if __name__=="__main__":
    unittest.main()
