"""Ensure unified GPT-Doug pytest CI includes the Bio-Gpt exact math cases."""
import unittest

from research_lab.tests import test_bio_gpt


def test_bio_gpt_exact_model_certificates():
    suite = unittest.TestLoader().loadTestsFromModule(test_bio_gpt)
    result = unittest.TestResult()
    suite.run(result)
    assert result.testsRun == 25, f"Bio-Gpt test count changed: {result.testsRun}"
    assert result.wasSuccessful(), {
        "failures": [(str(case), msg) for case, msg in result.failures],
        "errors": [(str(case), msg) for case, msg in result.errors],
    }
