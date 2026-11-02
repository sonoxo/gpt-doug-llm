"""Deny-by-default tests for Glass Onion's 15 video source inventory."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import glass_onion_15_catalog as g

class GateTests(unittest.TestCase):
    def setUp(self): self.data=g.load()
    def test_all_slots(self): self.assertEqual(g.validate(self.data)["slots"],15)
    def test_all_references(self): self.assertEqual(g.validate(self.data)["sourceReferences"],16)
    def test_graph_nodes(self): self.assertEqual(len(g.ontology(self.data)["nodes"]),37)
    def test_execution_disabled(self):
        d=copy.deepcopy(self.data);d["slots"][0]["policy"]["allowExecution"]=True
        with self.assertRaises(ValueError):g.validate(d)
    def test_autoclone_disabled(self):
        d=copy.deepcopy(self.data);d["slots"][0]["policy"]["allowAutoCloning"]=True
        with self.assertRaises(ValueError):g.validate(d)
    def test_no_untrusted_urls(self):
        d=copy.deepcopy(self.data);d["slots"][0]["selectedRepos"][0]["url"]="http://127.0.0.1/admin"
        with self.assertRaises(ValueError):g.validate(d)
    def test_no_fake_repo_hostnames(self):
        d=copy.deepcopy(self.data);d["slots"][0]["selectedRepos"][0]["url"]="https://github.com.evil.test/a/b"
        with self.assertRaises(ValueError):g.validate(d)
    def test_license_gate(self):
        d=copy.deepcopy(self.data);d["slots"][0]["selectedRepos"][0]["licenseReviewRequired"]=False
        with self.assertRaises(ValueError):g.validate(d)
    def test_spoken_claims_not_verified(self):
        d=copy.deepcopy(self.data);d["source"]["speakerClaimsIndependentlyVerified"]=True
        with self.assertRaises(ValueError):g.validate(d)
    def test_gitlab_canonical(self):
        d=next(s for s in self.data["slots"] if s["rank"]==4)
        self.assertEqual(d["selectedRepos"][0]["url"],g.GITLAB)
    def test_replacements(self): self.assertEqual(g.validate(self.data)["openSourceSubstitutions"],2)
    def test_probe_prohibits_external_targets(self):
        with self.assertRaises(ValueError):g.probe("https://example.org/")
if __name__=="__main__":unittest.main()
