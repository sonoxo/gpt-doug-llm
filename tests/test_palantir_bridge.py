import unittest
from unittest.mock import Mock

from doug_core.runtime import DougRuntime
from palantir_bridge import DougPalantirBridge


class PalantirBridgeTests(unittest.TestCase):
    def test_ground_prompt_uses_foundry_objects(self):
        client = Mock()
        client.list_objects.return_value = {
            "data": [{"id": "asset-1", "status": "ready"}],
            "nextPageToken": None,
        }
        bridge = DougPalantirBridge(foundry=client, doug=DougRuntime())
        grounded = bridge.ground_prompt("Summarize readiness", "ops", "Asset", page_size=5)
        self.assertIn("palantir-foundry", grounded)
        self.assertIn("asset-1", grounded)
        self.assertIn("Summarize readiness", grounded)
        client.list_objects.assert_called_once_with("ops", "Asset", page_size=5)

    def test_doug_analysis_receives_grounded_context(self):
        client = Mock()
        client.list_objects.return_value = {"data": [{"id": "asset-2"}]}
        runtime = Mock()
        runtime.analyze.return_value = {"task": "ok"}
        bridge = DougPalantirBridge(foundry=client, doug=runtime)
        result = bridge.doug_analysis("Inspect", "ops", "Asset")
        self.assertTrue(result["grounded"])
        prompt = runtime.analyze.call_args.args[0]
        self.assertIn("asset-2", prompt)
        self.assertIn("USER_REQUEST=Inspect", prompt)


if __name__ == "__main__":
    unittest.main()
