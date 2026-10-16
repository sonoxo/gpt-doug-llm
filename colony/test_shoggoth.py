import tempfile
import unittest
from pathlib import Path
from colony.shoggoth import Shoggoth

class ShoggothTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.agent=Shoggoth(str(Path(self.tmp.name)/"colony.sqlite3"))
 def tearDown(self):
  self.agent.close()
  self.tmp.cleanup()
 def test_routing_to_specialist(self):
  r=self.agent.route("biochip","Analyze digital biochip signal")
  self.assertEqual(r["agent"],"gpt-biochip")
  self.assertEqual(r["status"],"needs_evidence")
 def test_review_evidence_only(self):
  r=self.agent.route("organ","Review a publication",["doi:10/example"])
  self.assertEqual(r["status"],"awaiting_human_review")
 def test_reject_external_execution(self):
  with self.assertRaises(PermissionError):
   self.agent.route("cellular","Do something",action="operate_robot")
 def test_persistence_and_audit(self):
  self.agent.route("robotics","Compare simulated sensors")
  self.assertEqual(self.agent.status()["audit_events"],1)
  self.assertEqual(self.agent.status()["task_counts"][0]["count"],1)
 def test_unknown_domain(self):
  with self.assertRaises(ValueError):
   self.agent.route("unknown","Question")
if __name__=="__main__": unittest.main()
