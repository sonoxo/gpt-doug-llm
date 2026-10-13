"""Offline BioPineal public patent-reference regressions."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from research_lab.biopineal_patent import SOURCE, EQUATION, checked_balance, report, verify, terminal
ROOT=Path(__file__).resolve().parents[1]

class BioPinealTests(unittest.TestCase):
    def test_balanced(self):self.assertEqual(checked_balance(),{"Cl":0,"H":0,"Li":0,"O":0})
    def test_hydrogen_and_chlorine_products(self):self.assertEqual((EQUATION["H2"],EQUATION["Cl2"]),(1,1))
    def test_patent_identity(self):self.assertEqual(SOURCE["document_id"],"US 12760393 B1")
    def test_assignee_not_user(self):self.assertEqual(SOURCE["assignee"],"PolyPlus Battery Company")
    def test_no_ownership_claim(self):self.assertFalse(report()["patent"]["invention_owned_by_gpt_doug"])
    def test_no_official_verification(self):self.assertFalse(report()["patent"]["official_record_independently_verified"])
    def test_no_hardware_control(self):self.assertFalse(report()["physical_process_activated"])
    def test_nobel_not_claimed(self):self.assertFalse(report()["nobel_or_government_endorsement"])
    def test_toxicity_disclosed(self):self.assertIn("toxic",report()["hazard_disclosures"]["Cl2"])
    def test_unbalanced_rejected(self):
        e=dict(EQUATION);e["H2"]=2
        with self.assertRaises(ValueError):checked_balance(e)
    def test_extra_species_rejected(self):
        e=dict(EQUATION);e["CO2"]=1
        with self.assertRaises(ValueError):checked_balance(e)
    def test_noncanonical_coefficients_rejected(self):
        e={k:v*2 for k,v in EQUATION.items()}
        with self.assertRaises(ValueError):checked_balance(e)
    def test_digest_reproducible(self):self.assertEqual(report(),report())
    def test_report_roundtrip(self):self.assertTrue(verify(report()))
    def test_digest_tampering_rejected(self):
        d=report();d["sha256"]="0"*64
        self.assertFalse(verify(d))
    def test_fake_ownership_rejected(self):
        d=report();d["patent"]["invention_owned_by_gpt_doug"]=True
        self.assertFalse(verify(d))
    def test_fake_process_activated_rejected(self):
        d=report();d["physical_process_activated"]=True
        self.assertFalse(verify(d))
    def test_terminal_has_hazards(self):self.assertIn("Cl2 toxic",terminal())
    def test_cli_from_any_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,"-m","research_lab.biopineal_patent","report"],cwd=ROOT,text=True,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            fp=Path(d)/"report.json";fp.write_text(p.stdout,encoding="utf-8")
            q=subprocess.run([sys.executable,"-m","research_lab.biopineal_patent","verify",str(fp)],cwd=ROOT,text=True,capture_output=True,timeout=10)
            self.assertEqual(q.returncode,0,q.stderr)
            self.assertTrue(json.loads(q.stdout)["integrity_verified"])
    def test_source_is_excerpt(self):self.assertEqual(SOURCE["source_kind"],"USER_SUPPLIED_PATENT_SEARCH_EXCERPT")
if __name__=="__main__":unittest.main()
