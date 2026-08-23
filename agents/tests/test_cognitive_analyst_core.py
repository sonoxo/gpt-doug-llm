import unittest

from agents.cognitive_analyst_core import (
    ClaimKind,
    CognitiveAnalystCore,
    Observation,
)


class CognitiveAnalystCoreTests(unittest.TestCase):
    def test_observation_requires_known_source(self):
        core = CognitiveAnalystCore()
        with self.assertRaises(ValueError):
            core.commit_judgment("fact", ClaimKind.OBSERVATION, ["missing"], 0.9)

    def test_unsupported_inference_is_confidence_capped(self):
        core = CognitiveAnalystCore()
        judgment = core.commit_judgment("possible explanation", ClaimKind.INFERENCE, confidence=0.95)
        self.assertLessEqual(judgment.confidence, 0.35)

    def test_high_consequence_irreversible_action_is_blocked(self):
        core = CognitiveAnalystCore()
        core.collect([Observation("s1", "verified state", reliability=0.95)])
        gate = core.gate_action(
            "external consequential action",
            ["s1"],
            reversible=False,
            consequence="high",
        )
        self.assertFalse(gate.allowed)

    def test_strategy_feedback_changes_preference(self):
        core = CognitiveAnalystCore()
        core.reflect("assumption-check", True)
        core.reflect("assumption-check", True)
        core.reflect("single-hypothesis", False, "confirmation bias")
        preferred = core.preferred_strategies()
        self.assertEqual(preferred[0][0], "assumption-check")
        self.assertGreater(preferred[0][1], preferred[1][1])

    def test_processing_deduplicates_by_normalized_text(self):
        core = CognitiveAnalystCore()
        core.collect([
            Observation("weak", "Same observation", reliability=0.2),
            Observation("strong", " same   observation ", reliability=0.9),
        ])
        processed = core.process()
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0].source_id, "strong")


if __name__ == "__main__":
    unittest.main()
