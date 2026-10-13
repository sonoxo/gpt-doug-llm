"""Regression tests for provenance-linked BioPineal Phase II."""
import copy
import unittest
from research_lab.biopineal_phase2 import graph, flow, report, verify, validate_graph

class Phase2Tests(unittest.TestCase):
    def test_graph_valid(self): self.assertTrue(validate_graph(graph()))
    def test_identity_unverified(self):
        self.assertFalse(graph()["official_record_verified"])
        self.assertFalse(graph()["technology_use_rights_verified"])
    def test_no_hardware(self): self.assertFalse(graph()["hardware_connected"])
    def test_graph_no_orphans(self):
        g=graph(); ids={n["id"] for n in g["nodes"]}
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in g["edges"]))
    def test_balance(self): self.assertEqual(set(flow()["element_residual"].values()), {0})
    def test_scaling(self):
        self.assertEqual(flow(3)["output_coefficients"]["LiOH"], 6)
        self.assertEqual(set(flow(3)["element_residual"].values()), {0})
    def test_reject_negative(self):
        with self.assertRaises(ValueError): flow(-1)
    def test_reject_fraction(self):
        with self.assertRaises(ValueError): flow(0.5)
    def test_reject_bool(self):
        with self.assertRaises(ValueError): flow(True)
    def test_reject_excess(self):
        with self.assertRaises(ValueError): flow(1000001)
    def test_no_yield(self): self.assertFalse(flow()["conversion_or_yield_predicted"])
    def test_hazards(self): self.assertIn("toxic",flow()["hazards"]["Cl2"])
    def test_report_verified(self): self.assertTrue(verify(report()))
    def test_false_verification_rejected(self):
        r=report(); r["graph"]["official_record_verified"]=True
        self.assertFalse(verify(r))
    def test_ownership_tamper_rejected(self):
        r=report(); r["graph"]["technology_use_rights_verified"]=True
        self.assertFalse(verify(r))
    def test_digest_tamper_rejected(self):
        r=report(); r["sha256"]="0"*64
        self.assertFalse(verify(r))
    def test_deterministic(self): self.assertEqual(report(),report())
    def test_extra_node_rejected(self):
        r=report();r["graph"]["nodes"].append({"id":"fake","kind":"claim"})
        self.assertFalse(verify(r))

if __name__ == "__main__": unittest.main()
