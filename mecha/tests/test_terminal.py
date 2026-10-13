import copy
import unittest

from mecha.render.terminal import render_frame,render_frames
from mecha.snapshot import build_snapshot
from mecha.robotics import simulate_rover
from test_contracts import FIXTURE


class TestTerminal(unittest.TestCase):
    def setUp(self):
        self.snapshot=build_snapshot(FIXTURE,simulate_rover(FIXTURE))

    def test_readable_six_channel_labelled_visualization(self):
        a=render_frame(self.snapshot,frame=0,width=80)
        for word in ('MECHA','SYNTHETIC','RESEARCH_ONLY','No real robotics connected',
                     'X:', 'Y:', 'Z:', 'D4 TIME:', 'D5 MEMORY:', 'D6 COMPUTE:'):
            self.assertIn(word,a)
        self.assertNotIn('\x1b',a)
        self.assertIn('+',a)
        self.assertEqual(a,render_frame(self.snapshot,frame=0,width=80))
        self.assertNotEqual(a,render_frame(self.snapshot,frame=1,width=80))

    def test_missing_signal_safe(self):
        self.assertIn('NO SIGNAL',render_frame(None))

    def test_invalid_frame_width_bounds(self):
        for kwargs in ({'frame':-1},{'frame':1001},{'width':10},{'width':161},
                       {'frame':True},{'width':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                render_frame(self.snapshot,**kwargs)
        for frames in (0,1001,-1,True):
            with self.subTest(frames=frames),self.assertRaises(ValueError):
                render_frames(self.snapshot,frames=frames)

    def test_malicious_user_label_cannot_inject_terminal_escape(self):
        snap=copy.deepcopy(self.snapshot)
        snap['channels']['memory']='\x1b[8msecret\x1b[0m'
        with self.assertRaises(ValueError):render_frame(snap)
        self.assertNotIn('\x1b',render_frame(self.snapshot))

    def test_frame_list_finite_and_bounded(self):
        values=render_frames(self.snapshot,frames=3,width=50)
        self.assertEqual(len(values),3)
        self.assertNotEqual(values[0],values[2])
        self.assertTrue(all(len(x)<6000 for x in values))


if __name__=='__main__':unittest.main()
