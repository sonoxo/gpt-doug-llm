"""Include all Cure Swarm offline validation cases in GPT-Doug unified CI."""
import unittest

from research_lab.tests import test_cure_swarm


def test_cure_swarm_ontology_and_evidence_gate():
    suite = unittest.TestLoader().loadTestsFromModule(test_cure_swarm)
    results = unittest.TestResult()
    suite.run(results)
    assert results.testsRun == 35, f"unexpected number of Cure Swarm tests: {results.testsRun}"
    assert results.wasSuccessful(), {
        "failures": [(str(test), message) for test, message in results.failures],
        "errors": [(str(test), message) for test, message in results.errors],
    }
