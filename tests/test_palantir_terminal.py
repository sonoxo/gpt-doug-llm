import unittest
from unittest.mock import Mock

from palantir_terminal import handle_palantir_command


class PalantirTerminalTests(unittest.TestCase):
    def setUp(self):
        self.bridge = Mock()
        self.bridge.status.return_value = {"bridge": "ready"}
        self.bridge.foundry.list_ontologies.return_value = {"data": [{"apiName": "ops"}]}
        self.bridge.foundry.list_objects.return_value = {"data": [{"id": "1"}]}
        self.bridge.foundry.apply_action.return_value = {"validation": {"result": "VALID"}}
        self.bridge.ground_prompt.return_value = "grounded prompt"

    def test_status(self):
        result = handle_palantir_command("/palantir", self.bridge)
        self.assertTrue(result.handled)
        self.assertIn("ready", result.output)

    def test_ask_returns_grounded_prompt_for_normal_doug_pipeline(self):
        result = handle_palantir_command("/palantir ask ops Asset What is ready?", self.bridge)
        self.assertTrue(result.handled)
        self.assertEqual(result.grounded_prompt, "grounded prompt")
        self.bridge.ground_prompt.assert_called_once_with("What is ready?", "ops", "Asset")

    def test_action_requires_human_approval_callback(self):
        denied = handle_palantir_command(
            '/palantir action ops UpdateAsset {"id":"1"}',
            self.bridge,
            approve_write=lambda _message: False,
        )
        self.assertIn("CANCELLED", denied.output)
        self.bridge.foundry.apply_action.assert_not_called()

        allowed = handle_palantir_command(
            '/palantir action ops UpdateAsset {"id":"1"}',
            self.bridge,
            approve_write=lambda _message: True,
        )
        self.assertIn("VALID", allowed.output)
        self.bridge.foundry.apply_action.assert_called_once_with("ops", "UpdateAsset", {"id": "1"})


if __name__ == "__main__":
    unittest.main()
