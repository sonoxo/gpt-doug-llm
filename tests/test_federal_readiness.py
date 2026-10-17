import unittest
from scripts.federal_readiness import audit, GATES

class FederalReadinessTests(unittest.TestCase):
    def test_empty_defaults_to_incomplete(self):
        result = audit({"evidence": {}})
        self.assertEqual(len(result["gates"]), 6)
        self.assertTrue(all(g["status"] == "incomplete" for g in result["gates"].values()))
    def test_unreviewed_assertion_cannot_pass(self):
        result = audit({"evidence": {"business": {"uei": {"status": "verified", "reference": "proof"}}}})
        self.assertEqual(result["gates"]["business"]["evidence"]["uei"]["status"], "unverified")
    def test_full_review_is_evidence_only(self):
        fields = GATES["capability"][1]
        manifest = {"evidence": {"capability": {f: {"status": "verified", "reviewed": True, "reviewer": "Reviewer", "reference": "approved-ref"} for f in fields}}}
        result = audit(manifest)
        self.assertEqual(result["gates"]["capability"]["status"], "evidence_reviewed")
        self.assertEqual(result["status"], "evidence_review_only")

if __name__ == "__main__":
    unittest.main()
