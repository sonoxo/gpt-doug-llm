"""Offline CL1 full-body tests: no extra packages, hardware, or network calls."""
from __future__ import annotations

import contextlib
import io
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

_SOURCE = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SOURCE))

from cl1_body_terminal import (BONE, TISSUE, NEURAL, BIOCHIP,
                              BodyCanvas, geometry, run)


class BodyGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.points=geometry('normal')

    def test_full_body_contains_all_anatomical_regions(self):
        self.assertGreater(len(self.points), 30000)
        xs=[x for x,y,z,k in self.points]
        ys=[y for x,y,z,k in self.points]
        self.assertGreater(max(ys),2.8)
        self.assertLess(min(ys),-2.6)
        self.assertLess(min(xs),-1.0)
        self.assertGreater(max(xs),1.0)
        kinds={p[3] for p in self.points}
        self.assertEqual(kinds,{BONE,TISSUE,NEURAL,BIOCHIP})

    def test_both_arms_and_legs_present(self):
        arms=[p for p in self.points if p[3]==BONE and p[1]>.4 and abs(p[0])>.8]
        legs=[p for p in self.points if p[3]==BONE and p[1]<-1.4 and abs(p[0])>.3]
        self.assertGreater(len(arms),900)
        self.assertGreater(len(legs),2000)
        self.assertTrue(any(p[0]>0 for p in arms))
        self.assertTrue(any(p[0]<0 for p in arms))
        self.assertTrue(any(p[0]>0 for p in legs))
        self.assertTrue(any(p[0]<0 for p in legs))

    def test_mesh_is_deterministic_and_scaled(self):
        self.assertIs(geometry('normal'),geometry('normal'))
        self.assertLess(len(geometry('light')),len(self.points))
        with self.assertRaises(ValueError):
            geometry('ultra')

    def test_projection_contains_binary_only_and_real_depth(self):
        c=BodyCanvas(self.points,110,58)
        frame=c.render(color=False)
        self.assertTrue(set(frame)<=set(' 01\n'))
        self.assertEqual(len(frame.splitlines()),58)
        self.assertTrue(all(len(x)==110 for x in frame.splitlines()))
        self.assertGreater(frame.count('0')+frame.count('1'),300)
        c.yaw=0.85
        self.assertNotEqual(frame,c.render(color=False))

    def test_views_and_layer_filters_change_appearance(self):
        c=BodyCanvas(self.points,100,52)
        fusion=c.render(color=False)
        c.mode='SKELETON'
        skeleton=c.render(color=False)
        c.mode='BODY'
        body=c.render(color=False)
        c.mode='NEURAL'
        neural=c.render(color=False)
        self.assertNotEqual(fusion,skeleton)
        self.assertNotEqual(skeleton,body)
        self.assertNotEqual(neural,body)
        c.view='HEAD'
        self.assertNotEqual(neural,c.render(color=False))

    def test_single_frame_needs_no_model_or_network(self):
        stdout=io.StringIO()
        with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(run(['--once','--no-color','--width','90','--height','42']),0)
        text=stdout.getvalue()
        self.assertIn('FULL BODY',text)
        self.assertIn('NO LIVING NEURONS OR HARDWARE',text)
        self.assertEqual(len(text.splitlines()),48)
        self.assertNotIn('\x1b',text)

    def test_bound_cli_inputs(self):
        for flags in (["--fps","0"],["--height","9"],["--width","220"],
                      ["--frames","99999"]):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run(list(flags))


if __name__=='__main__':
    unittest.main()