"""Run the complete exact multidimensional research suite inside unified CI.

The canonical 28 offline unittest cases live in research_lab/tests. This shim
ensures existing pytest jobs cover them without duplicating the tests.
"""
import unittest

from research_lab.tests import test_multidimensional


def test_exact_multidimensional_research_suite():
    suite = unittest.TestLoader().loadTestsFromModule(test_multidimensional)
    result = unittest.TestResult()
    suite.run(result)
    assert result.testsRun == 28, f"unexpected research test count: {result.testsRun}"
    assert result.wasSuccessful(), {
        "failures": [(str(case), message) for case, message in result.failures],
        "errors": [(str(case), message) for case, message in result.errors],
    }
