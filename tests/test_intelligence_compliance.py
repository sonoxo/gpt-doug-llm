import unittest
from datetime import datetime, timezone

from intelligence_compliance import (
    IntelligenceClaim,
    SourceProvenance,
    external_action_allowed,
    validate_claim,
    validate_claim_batch,
    validate_provenance,
)


def source(**changes):
    values = dict(
        source_id="src-1",
        source_type="public_web",
        classification="public",
        retrieved_at=datetime.now(timezone.utc),
        source_url="https://example.com/report",
    )
    values.update(changes)
    return SourceProvenance(**values)


def claim(**changes):
    values = dict(
        provenance=source(),
        claim="The source states a documented public fact.",
        claim_type="fact",
        confidence="high",
        corroboration_count=1,
    )
    values.update(changes)
    return IntelligenceClaim(**values)


class IntelligenceComplianceTests(unittest.TestCase):
    def test_valid_public_provenance(self):
        self.assertTrue(validate_provenance(source()).valid)

    def test_rejects_non_public_classification(self):
        result = validate_provenance(source(classification="classified"))
        self.assertFalse(result.valid)
        self.assertIn("source classification is not permitted", result.reasons)

    def test_rejects_invalid_source_url(self):
        self.assertFalse(validate_provenance(source(source_url="file:///secret/report")).valid)

    def test_requires_timezone_aware_retrieval_time(self):
        naive = datetime(2026, 8, 22, 3, 0, 0)
        self.assertFalse(validate_provenance(source(retrieved_at=naive)).valid)

    def test_nonfactual_claim_requires_limitations(self):
        result = validate_claim(
            claim(
                claim_type="inference",
                confidence="moderate",
                limitations=(),
            )
        )
        self.assertFalse(result.valid)
        self.assertIn("non-factual claims must record at least one limitation", result.reasons)

    def test_external_action_requires_all_reviews(self):
        result = external_action_allowed(claim())
        self.assertFalse(result.valid)
        self.assertIn("privacy review is required before external action", result.reasons)
        self.assertIn("operational safety review is required before external action", result.reasons)
        self.assertIn("human approval is required before external action", result.reasons)

    def test_external_action_allowed_after_reviews(self):
        reviewed = claim(
            privacy_review=True,
            operational_safety_review=True,
            human_approved=True,
        )
        self.assertTrue(external_action_allowed(reviewed).valid)

    def test_batch_validation_identifies_failing_index(self):
        bad = claim(confidence="certain")
        result = validate_claim_batch([claim(), bad])
        self.assertFalse(result.valid)
        self.assertTrue(any(reason.startswith("record[1]:") for reason in result.reasons))


if __name__ == "__main__":
    unittest.main()
