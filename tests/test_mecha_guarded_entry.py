import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts'/'doug-max'


def launch(*args):
    return subprocess.run(['bash',str(SCRIPT),'mecha',*map(str,args)],
                          cwd=ROOT,capture_output=True,text=True,timeout=20)


class TestGuardedEntry(unittest.TestCase):
    def test_launcher_syntax(self):
        r=subprocess.run(['bash','-n',str(SCRIPT)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_mecha_route_uses_existing_guardrail_preflight(self):
        source=SCRIPT.read_text(encoding='utf-8')
        self.assertIn('mecha)',source)
        self.assertIn('python3 -m mecha.cli "$@"',source)
        self.assertIn('agents.galactic_guardrails',source)
        self.assertIn('read_only_mode=0',source)
        exempt=source.split('read_only_mode=0',1)[1].split('if [[ "$read_only_mode"',1)[0]
        self.assertNotIn('mecha)',exempt)

    def test_user_visible_doctor_is_research_only(self):
        r=launch('doctor')
        self.assertEqual(r.returncode,0,r.stderr)
        d=json.loads(r.stdout)
        self.assertEqual(d['authority'],'RESEARCH_ONLY')
        self.assertFalse(d['real_world_actuation'])
        self.assertEqual(d['external_calls'],0)

    def test_launcher_quietly_rejects_non_synthetic_motion_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture=p/'live.json'
            fixture.write_text(json.dumps({'source_kind':'LIVE','motor_command':'FORWARD'}))
            r=launch('demo','--fixture',fixture,'--input-root',p)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('error',json.loads(r.stderr))
            self.assertEqual(len(list(p.iterdir())),1)

    def test_push_event_protected_file_check_compares_before_sha(self):
        workflow=(ROOT/'.github/workflows/mecha-research.yml').read_text()
        self.assertIn('github.event_name',workflow)
        self.assertIn('github.event.before',workflow)
        self.assertIn('BASE="$PUSH_BEFORE"',workflow)
        self.assertIn('git cat-file -e "$BASE^{commit}"',workflow)
        self.assertIn('git diff --exit-code "$BASE" HEAD',workflow)
        self.assertIn('git merge-base origin/main HEAD',workflow)

    def test_bell_state_through_guarded_launcher(self):
        p=ROOT/'mecha'/'examples'/'bell-state.json'
        r=launch('quantum',p,'--input-root',p.parent,'--budget-units','200')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['compute_units_used'],12)


if __name__=='__main__':unittest.main()
