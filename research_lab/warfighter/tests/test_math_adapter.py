import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from research_lab.warfighter.hilbert_adapter import analyze_math, verify_math

class TestAdapterContract(unittest.TestCase):
    def test_dispatch_calls_expected_pure_math_functions(self):
        calls=[]
        fake=types.ModuleType('research_lab.bio_hilbert')
        fake.analyze=lambda p: calls.append(p) or {'status':'CERTIFIED_SIX_CHANNEL_HILBERT_MODEL','input':p,'finite_dimensions':36}
        fake.verify=lambda x: x.get('status')=='CERTIFIED_SIX_CHANNEL_HILBERT_MODEL'
        with patch.dict(sys.modules,{'research_lab.bio_hilbert':fake}):
            problem={'modes':6,'steps':3,'model':{},'initial':[]}
            result=analyze_math('bio-hilbert',problem)
            self.assertEqual(result['report']['finite_dimensions'],36)
            self.assertTrue(verify_math('bio-hilbert',result))
            self.assertEqual(calls,[problem])
            self.assertEqual(result['authority'],'RESEARCH_ONLY')
            self.assertEqual(result['model_scope'],'mathematical_toy_model_only')

    def test_bounds_and_unknown_engine(self):
        for p in [{'modes':129,'steps':1},{'modes':6,'steps':9}]:
            with self.assertRaises(ValueError):
                analyze_math('bio-hilbert',p)
        with self.assertRaises(ValueError):
            analyze_math('no-such-engine',{})

    def test_inconclusive_replay_does_not_become_proof(self):
        fake=types.ModuleType('research_lab.multidimensional')
        fake.analyze=lambda p: {'input':p,'proof':{'status':'INCONCLUSIVE'}}
        fake.verify=lambda r: r['proof']['status']=='INCONCLUSIVE'
        with patch.dict(sys.modules,{'research_lab.multidimensional':fake}):
            got=analyze_math('exact-linear',{'matrix':[[2]]})
            self.assertEqual(got['proof_status'],'INCONCLUSIVE')
            self.assertTrue(verify_math('exact-linear',got))
            self.assertNotIn('operational_ready',got)

class TestRealEngine(unittest.TestCase):
    def test_existing_engine_when_available(self):
        try:
            from research_lab import bio_hilbert
        except ImportError:
            self.skipTest('existing main repository math engines not available in local source mirror')
        demo=bio_hilbert.demo_problem()
        result=analyze_math('bio-hilbert',demo)
        self.assertEqual(result['report']['finite_dimensions'],36)
        self.assertTrue(verify_math('bio-hilbert',result))
        with self.assertRaises(ValueError):
            analyze_math('bio-hilbert',dict(demo,modes=129))
