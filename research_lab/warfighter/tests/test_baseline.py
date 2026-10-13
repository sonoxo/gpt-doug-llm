import copy
import json
import unittest
from pathlib import Path
from research_lab.warfighter.baseline import run_baseline

ROOT=Path(__file__).resolve().parents[1]

class TestBaseline(unittest.TestCase):
    def setUp(self):
        self.demo=json.loads((ROOT/'examples/synthetic_training_defense.json').read_text())

    def test_deterministic_what_if(self):
        old=copy.deepcopy(self.demo)
        a=run_baseline(self.demo)
        self.assertEqual(a,run_baseline(self.demo))
        self.assertEqual(self.demo,old)
        self.assertEqual(a['metrics']['training_readiness_pct']['hypothetical'],73)
        self.assertEqual(a['metrics']['patch_compliance_pct']['hypothetical'],79)
        self.assertEqual(a['metrics']['sensor_health_pct']['hypothetical'],96)
        self.assertEqual(a['authority'],'RESEARCH_ONLY')
        self.assertNotIn('mission_readiness',a)

    def test_cap_and_invalid_deltas(self):
        self.demo['fixture']['sensor_health_pct']=99
        self.assertEqual(run_baseline(self.demo)['metrics']['sensor_health_pct']['hypothetical'],100)
        for x in (True,-1,21,3.0):
            with self.subTest(value=x),self.assertRaises(ValueError):
                run_baseline(self.demo,what_if_delta=x)
