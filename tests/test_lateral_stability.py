"""Replay exact disturbance bounds for title-inspired (not video-derived) model."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from research_lab import lateral_stability as m

ROOT=Path(__file__).resolve().parents[1]

class StabilityTests(unittest.TestCase):
    def test_demo_certificate(self):
        r=m.analyze(m.example())
        self.assertEqual(r['status'],'PROVED_TOY_SUPPORT_INVARIANT')
        self.assertEqual(r['proof']['matrix_infinity_norm_mu'],'3/4')
        self.assertEqual(r['proof']['input_infinity_norm_beta'],'1/2')
        self.assertEqual(r['proof']['uniform_infinity_state_bound'],'1/20')
        self.assertTrue(r['proof']['all_steps_position_in_support_proven'])
        self.assertTrue(m.verify(r))

    def test_exact_update(self):
        r=m.analyze(m.example())
        self.assertEqual(r['A'],[['3/4','0'],['-1/2','0']])
        self.assertEqual(r['B'],['1/4','1/2'])
        self.assertEqual(r['trajectory'][1]['position'],'3/80')
        self.assertEqual(r['trajectory'][1]['velocity'],'-1/40')

    def test_worst_disturbance_bound(self):
        r=m.analyze(m.example())
        mu=Fraction(r['proof']['matrix_infinity_norm_mu'])
        beta=Fraction(r['proof']['input_infinity_norm_beta'])
        D=Fraction(r['proof']['bounded_disturbance'])
        self.assertEqual(beta*D/(1-mu),Fraction(1,50))

    def test_unsafe_support_width_not_proven(self):
        v=m.example()
        v['support_half_width']='1/1000'
        r=m.analyze(v)
        self.assertEqual(r['status'],'UNCERTIFIED_FOR_ALL_DISTURBANCES')
        self.assertFalse(r['proof']['finite_samples_inside_support'])

    def test_unstable_matrix_not_certified(self):
        v=m.example()
        v['model']['dt']='1'
        v['model']['kp']='10'
        v['model']['kd']='0'
        r=m.analyze(v)
        self.assertIsNone(r['proof']['uniform_infinity_state_bound'])
        self.assertEqual(r['status'],'UNCERTIFIED_FOR_ALL_DISTURBANCES')

    def test_rejects_exceeding_bound(self):
        v=m.example()
        v['disturbances'][0]='1/10'
        with self.assertRaises(ValueError): m.analyze(v)

    def test_reject_float_inputs(self):
        for v in (0.1,True,None,[],{}):
            with self.subTest(v=v),self.assertRaises(ValueError):m.exact(v)

    def test_no_extra_fields(self):
        v=m.example()
        v['motor_command']='run'
        with self.assertRaises(ValueError):m.analyze(v)

    def test_max_disturbances(self):
        v=m.example()
        v['disturbances']=['0']*65
        with self.assertRaises(ValueError):m.analyze(v)

    def test_tampered_report_fails(self):
        r=m.analyze(m.example())
        for section,field,new in [('proof','all_steps_position_in_support_proven',False),('proof','matrix_infinity_norm_mu','0')]:
            with self.subTest(field=field):
                data=copy.deepcopy(r)
                data[section][field]=new
                self.assertFalse(m.verify(data))

    def test_metadata_clearly_limited(self):
        r=m.analyze(m.example())
        self.assertIn('metadata only',r['source_provenance']['provenance'])
        self.assertIn('no physical stability guarantee',r['scope'])

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=subprocess.run([sys.executable,'-m','research_lab.lateral_stability','demo'],cwd=ROOT,text=True,capture_output=True,timeout=10)
            self.assertEqual(r.returncode,0,r.stderr)
            report=Path(tmp)/'report.json'
            report.write_text(r.stdout)
            p=subprocess.run([sys.executable,'-m','research_lab.lateral_stability','verify',str(report)],cwd=ROOT,text=True,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('VERIFIED',p.stdout)

if __name__=='__main__': unittest.main()
