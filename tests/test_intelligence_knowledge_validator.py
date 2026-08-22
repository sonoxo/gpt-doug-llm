import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_intelligence_knowledge import validate_jsonl, validate_record


class IntelligenceKnowledgeValidatorTests(unittest.TestCase):
    def test_complete_public_record_passes(self):
        record = {
            "id": "src-1",
            "topic": "analytic standards",
            "summary": "Public guidance summary",
            "attribution": "ODNI",
            "source_url": "https://www.dni.gov/example",
            "classification": "public",
        }
        self.assertEqual(validate_record(record, "test.jsonl", 1), [])

    def test_legacy_record_reports_provenance_gaps(self):
        record = {
            "id": "src-1",
            "topic": "history",
            "summary": "Historical summary",
            "attribution": "CIA/Wikipedia",
        }
        findings = validate_record(record, "legacy.jsonl", 2)
        messages = {finding.message for finding in findings}
        self.assertIn("legacy record has no source_url provenance", messages)
        self.assertIn("legacy record has no classification metadata", messages)

    def test_sensitive_attribution_label_requires_verification(self):
        record = {
            "id": "src-1",
            "topic": "tradecraft",
            "summary": "Training summary",
            "attribution": "CIA field manual",
            "source_url": "https://example.com/public-copy",
            "classification": "public",
        }
        findings = validate_record(record, "test.jsonl", 3)
        self.assertTrue(any("independent public-source verification" in f.message for f in findings))

    def test_invalid_classification_is_error(self):
        record = {
            "id": "src-1",
            "topic": "test",
            "summary": "test",
            "attribution": "test",
            "source_url": "https://example.com",
            "classification": "classified",
        }
        findings = validate_record(record, "test.jsonl", 4)
        self.assertTrue(any(f.level == "error" and "classification" in f.message for f in findings))

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.jsonl"
            path.write_text('{"id": "ok"}\nnot-json\n', encoding="utf-8")
            findings = validate_jsonl(path)
        self.assertTrue(any(f.level == "error" and "invalid JSON" in f.message for f in findings))

    def test_non_object_json_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "list.jsonl"
            path.write_text(json.dumps(["not", "object"]) + "\n", encoding="utf-8")
            findings = validate_jsonl(path)
        self.assertTrue(any(f.level == "error" and "JSON object" in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
