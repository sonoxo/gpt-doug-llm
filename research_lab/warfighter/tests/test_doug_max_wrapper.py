"""Shell integration regression for the existing GPT-Doug launcher."""
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'scripts'/'doug-max'

@unittest.skipUnless(SCRIPT.is_file(),'full upstream checkout not available')
class TestDougMaxWarfighter(unittest.TestCase):
    def test_launcher_shell_syntax(self):
        result=subprocess.run(['bash','-n',str(SCRIPT)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_warfighter_route_preserves_execution_guardrail(self):
        content=SCRIPT.read_text(encoding='utf-8')
        self.assertIn('warfighter|warfighter-research)',content)
        self.assertIn('python3 -m research_lab.warfighter.cli "$@"',content)
        self.assertIn('agents.galactic_guardrails',content)
        read_only=content.split('read_only_mode=0',1)[1].split('if [[ "$read_only_mode"',1)[0]
        self.assertNotIn('warfighter|warfighter-research',read_only)
