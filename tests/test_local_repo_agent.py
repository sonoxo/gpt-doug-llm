import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_repo_agent import LocalRepoAgent, bounded, choose_model, resolve_repo


class LocalRepoAgentTests(unittest.TestCase):
    def test_choose_model_prefers_requested_local_model(self):
        models = ["qwen2.5-coder:7b", "llama3:8b"]
        self.assertEqual(choose_model(models, "llama3:8b"), "llama3:8b")

    def test_choose_model_falls_back_to_installed_model(self):
        self.assertEqual(choose_model(["custom-local:latest"], "missing"), "custom-local:latest")

    def test_budget_bounds_reject_unbounded_values(self):
        self.assertEqual(bounded(24, 1, 64, "max steps"), 24)
        with self.assertRaises(ValueError):
            bounded(65, 1, 64, "max steps")

    def test_resolve_repo_requires_git_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                resolve_repo(str(root))
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            self.assertEqual(resolve_repo(str(root)), root.resolve())

    def test_node_final_gate_runs_typescript_tests_build_and_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            agent = LocalRepoAgent(root, model="test", state_dir=root / ".state")
            success = {"ok": True, "returncode": 0, "output": "ok"}
            with patch.object(agent, "_run_process", side_effect=[success, success, success, success]) as run:
                result = agent._tool_run_check("syntax", [])
            self.assertTrue(result["ok"])
            self.assertEqual(run.call_count, 4)
            self.assertEqual(result["output"], "TypeScript/tests/build/diff gates passed")

    def test_node_final_gate_stops_on_first_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            agent = LocalRepoAgent(root, model="test", state_dir=root / ".state")
            failure = {"ok": False, "returncode": 2, "output": "type error"}
            with patch.object(agent, "_run_process", return_value=failure) as run:
                result = agent._tool_run_check("syntax", [])
            self.assertFalse(result["ok"])
            self.assertEqual(run.call_count, 1)
            self.assertIn("typescript failed", result["output"])


if __name__ == "__main__":
    unittest.main()
