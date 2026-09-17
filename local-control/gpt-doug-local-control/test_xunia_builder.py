import tempfile
import unittest
from pathlib import Path
import agent_core

class BuilderTests(unittest.TestCase):
    def test_policy_has_builder_actions(self):
        caps=agent_core.POLICY["capabilities"]
        self.assertEqual(caps["workspace_status"], "read")
        self.assertEqual(caps["xunia_zyra_mission"], "write")

    def test_builder_requires_arm(self):
        with tempfile.TemporaryDirectory(dir=Path.home()) as td:
            root=Path(td)
            (root/"zyra_sleeper.py").write_text("print('x')")
            (root/"zyra_agent.py").write_text("print('x')")
            agent_core.disarm()
            with self.assertRaises(PermissionError):
                agent_core.execute({"type":"xunia_zyra_mission","root":str(root),"goal":"test"})

    def test_workspace_status_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=Path.home()) as td:
            root=Path(td)
            result=agent_core.execute({"type":"workspace_status","root":str(root)})
            self.assertEqual(result["root"], str(root.resolve()))
            self.assertFalse(result["builder_ready"])

if __name__ == "__main__": unittest.main()
