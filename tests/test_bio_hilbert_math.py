"""Unified pytest CI wrapper for the exact six-channel Hilbert model."""
import unittest

from research_lab.tests import test_bio_hilbert


def test_all_bio_hilbert_math_certificates():
    suite = unittest.TestLoader().loadTestsFromModule(test_bio_hilbert)
    result = unittest.TestResult()
    suite.run(result)
    assert result.testsRun == 30, f"unexpected bio Hilbert test count: {result.testsRun}"
    assert result.wasSuccessful(), {
        "failures": [(str(test), message) for test, message in result.failures],
        "errors": [(str(test), message) for test, message in result.errors],
    }
