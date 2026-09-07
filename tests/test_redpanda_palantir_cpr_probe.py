from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "redpanda-desktop" / "palantir_cpr_probe.py"
SPEC = importlib.util.spec_from_file_location("palantir_cpr_probe", MODULE_PATH)
assert SPEC and SPEC.loader
probe_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe_module)


class PalantirCprProbeTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        files = {
            "palantir_foundry.py": "VALUE = 1\n",
            "sovereignty_performance.py": (
                "import json\n"
                "print(json.dumps({\"palantir_infrastructure_controlled\": False, "
                "\"hardware\": {\"preferred_accelerator\": \"cpu\", "
                "\"accelerators\": [\"cpu\"], \"cpu_count\": 1, \"memory_bytes\": 1024}}))\n"
            ),
            "tools/palantir-toolbox/manifest.json": json.dumps({"manifest_version": 3}),
            "tools/palantir-toolbox/foundry.js": "export const ok = true;\n",
            "tools/palantir-toolbox/bridge/palantir_bridge.py": "VALUE = 1\n",
            "safety-shield/agents/knowledge/palantir-stack-v1.json": json.dumps(
                {"knowledge_id": "palantir-stack-v1"}
            ),
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_probe_passes_valid_local_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            result = probe_module.probe(root)
            self.assertTrue(result["ok"])
            self.assertFalse(result["writes_performed"])
            self.assertFalse(result["foundry_actions_called"])
            self.assertEqual(
                result["checks"]["sovereignty_runtime"]["preferred_accelerator"], "cpu"
            )

    def test_probe_fails_when_required_files_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = probe_module.probe(Path(tmp))
            self.assertFalse(result["ok"])
            self.assertIn("palantir_foundry.py", result["missing"])


if __name__ == "__main__":
    unittest.main()
