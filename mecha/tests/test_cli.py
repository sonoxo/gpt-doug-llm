import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_contracts import FIXTURE

ROOT=Path(__file__).resolve().parents[2]
ROVER=ROOT/'mecha'/'examples'/'synthetic-inspection-rover.json'
BELL=ROOT/'mecha'/'examples'/'bell-state.json'


def invoke(*args):
    env=dict(os.environ, PYTHONPATH=str(ROOT/'mecha'))
    return subprocess.run([sys.executable,'-m','mecha.cli',*map(str,args)],
                          cwd=ROOT,capture_output=True,text=True,env=env,timeout=15)


class TestCli(unittest.TestCase):
    def test_standalone_doctor_does_not_require_host(self):
        r=invoke('doctor')
        self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout)
        self.assertEqual(obj['implementation'],'SIMULATED_OFFLINE_V1')
        self.assertEqual(obj['authority'],'RESEARCH_ONLY')
        self.assertFalse(obj['connected_robot'])
        self.assertFalse(obj['real_world_actuation'])
        self.assertEqual(obj['external_calls'],0)
        self.assertEqual(obj['host_adapters'],'ADAPTER_UNAVAILABLE')

    def test_demo_deterministic_while_offline(self):
        args=['demo','--fixture',str(ROVER),'--input-root',str(ROVER.parent)]
        r=invoke(*args)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(r.stdout,invoke(*args).stdout)
        result=json.loads(r.stdout)
        self.assertEqual(result['snapshot']['channels']['x'],0.75)
        self.assertFalse(result['simulation']['REAL_WORLD_ACTUATION'])
        self.assertNotIn('operator',r.stdout)

    def test_watch_three_frames_and_quantum_math(self):
        r=invoke('watch','--fixture',str(ROVER),'--input-root',str(ROVER.parent),'--frames','3','--no-color')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(r.stdout.count('D4 TIME:'),3)
        self.assertNotIn('\x1b',r.stdout)
        q=invoke('quantum',str(BELL),'--input-root',str(BELL.parent),'--budget-units','200')
        self.assertEqual(q.returncode,0,q.stderr)
        data=json.loads(q.stdout)
        self.assertEqual(data['compute_units_used'],12)
        self.assertAlmostEqual(data['probabilities']['11'],0.5)

    def test_invalid_fixture_fails_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            invalid=dict(FIXTURE,source_kind='LIVE')
            (root/'bad.json').write_text(json.dumps(invalid))
            r=invoke('demo','--fixture',root/'bad.json','--input-root',root)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('error',json.loads(r.stderr))
            self.assertEqual([p.name for p in root.iterdir()],['bad.json'])

    def test_no_network_or_host_import_from_cli(self):
        source=(ROOT/'mecha'/'mecha'/'cli.py').read_text()
        for forbidden in ('requests.', 'urllib.request.', 'socket.', 'workers.xqe',
                          'from pineal', 'from agents', 'from research_lab'):
            self.assertNotIn(forbidden,source)


if __name__=='__main__':unittest.main()
