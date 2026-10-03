import tempfile
import unittest

from scripts.zyra_cte_demo import DemoController


class TestCTEDemoController(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.demo = DemoController(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_preview_is_counterfactual_only(self):
        result = self.demo.preview()

        self.assertTrue(
            result["simulation"]["allowed"]
        )
        self.assertFalse(
            result["real_state_mutated"]
        )

        state = self.demo.state()

        self.assertEqual(
            state["attempt"]["phase"],
            "PROPOSED",
        )

    def test_authorized_execution_commits(self):
        self.demo.authorize()

        result = self.demo.execute()

        self.assertEqual(
            result["result"]["status"],
            "COMMITTED",
        )

        self.assertEqual(
            [
                event["to_phase"]
                for event in result["events"]
            ],
            [
                "PROPOSED",
                "SIMULATED",
                "AUTHORIZED",
                "EXECUTING",
                "OBSERVED",
                "COMMITTED",
            ],
        )

    def test_drift_rolls_back(self):
        self.demo.authorize()

        result = self.demo.execute(
            drift=True,
        )

        self.assertEqual(
            result["result"]["status"],
            "ROLLED_BACK",
        )

        self.assertEqual(
            result["attempt"]["phase"],
            "ROLLED_BACK",
        )

    def test_consumed_receipt_replay_is_denied(self):
        self.demo.authorize()
        self.demo.execute()

        replay = self.demo.replay_receipt()

        self.assertEqual(
            replay["result"]["status"],
            "AUTHORIZATION_DENIED",
        )

    def test_request_binding_tamper_is_blocked(self):
        result = self.demo.tamper_test()

        self.assertTrue(result["blocked"])
        self.assertIn(
            "different request",
            result["reason"],
        )


if __name__ == "__main__":
    unittest.main()
