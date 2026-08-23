import unittest

from agents.adaptive_intelligence import AdaptiveIntel, Evidence


class AdaptiveIntelTests(unittest.TestCase):
    def test_index_deduplicates_and_keeps_stronger_source(self):
        ai = AdaptiveIntel()
        ai.absorb([
            Evidence("weak", "Same fact", reliability=0.2),
            Evidence("strong", " same   fact ", reliability=0.9),
        ])
        ranked = ai.index()
        self.assertEqual([e.source_id for e in ranked], ["strong"])

    def test_index_orders_by_evidence_score(self):
        ai = AdaptiveIntel()
        ai.absorb([
            Evidence("a", "alpha", reliability=0.4, corroboration=1),
            Evidence("b", "beta", reliability=0.9, corroboration=2),
        ])
        self.assertEqual(ai.index()[0].source_id, "b")

    def test_verify_flags_unknown_source(self):
        ai = AdaptiveIntel()
        ai.absorb([Evidence("doc", "supported fact", reliability=0.8)])
        result = ai.verify({"claim": ["missing"]})[0]
        self.assertFalse(result.supported)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("unsupported claim: claim", ai.snapshot()["issues"])

    def test_strategy_preference_adapts_from_feedback(self):
        ai = AdaptiveIntel()
        ai.record_outcome("plan-a", True)
        ai.record_outcome("plan-a", True)
        ai.record_outcome("plan-b", False)
        preferred = ai.preferred_strategies()
        self.assertEqual(preferred[0][0], "plan-a")
        self.assertGreater(preferred[0][1], preferred[1][1])


if __name__ == "__main__":
    unittest.main()
