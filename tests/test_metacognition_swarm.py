import unittest

from gpt_doug.metacognition import (
    Candidate, merge_review_signals, review_candidate, run_review_rounds,
)


class MetacognitionSwarmTests(unittest.TestCase):
    def test_empty_candidate_is_held(self):
        review = review_candidate(Candidate(text=""))
        self.assertIn("candidate_text_missing", review.blockers)
        self.assertEqual(review.next_action, "gather_evidence")

    def test_complete_candidate_has_no_known_blockers(self):
        candidate = Candidate(
            text="Example recommendation",
            evidence=("source A", "source B", "source C"),
            assumptions=(),
            risks=(),
            tests=("unit test", "integration test", "policy test"),
        )
        review = review_candidate(candidate)
        self.assertEqual(review.blockers, ())
        self.assertEqual(review.next_action, "human_review_or_policy_gated_execution")

    def test_rounds_are_bounded(self):
        with self.assertRaises(ValueError):
            run_review_rounds(Candidate(text="x"), max_rounds=99)
        self.assertEqual(len(run_review_rounds(Candidate(text="x"), max_rounds=2)), 2)

    def test_aggregation_holds_if_any_blocker(self):
        weak = review_candidate(Candidate(text=""))
        result = merge_review_signals([weak])
        self.assertEqual(result["decision"], "hold")
        self.assertIn("candidate_text_missing", result["blockers"])


if __name__ == "__main__":
    unittest.main()
