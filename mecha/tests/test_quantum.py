import copy
import unittest
from mecha.quantum import simulate_quantum

BELL={'qubits':2,'initial_basis':0,
      'gates':[{'gate':'H','target':0},{'gate':'CNOT','control':0,'target':1}],
      'shots':0,'seed':0}


class TestQuantum(unittest.TestCase):
    def test_bell_probabilities_and_budget_are_classical(self):
        r=simulate_quantum(BELL,budget_units=200)
        self.assertAlmostEqual(r['probabilities']['00'],0.5,places=12)
        self.assertAlmostEqual(r['probabilities']['11'],0.5,places=12)
        self.assertEqual(r['probabilities']['01'],0)
        self.assertEqual(r['probabilities']['10'],0)
        self.assertEqual(r['compute_units_used'],12)
        self.assertFalse(r['quantum_hardware_used'])
        self.assertTrue(r['classical_simulation'])
        self.assertEqual(r['authority'],'RESEARCH_ONLY')
        self.assertEqual(r['source_kind'],'SYNTHETIC')

    def test_two_hadamards_restore_start_state(self):
        p={'qubits':1,'initial_basis':0,'gates':[{'gate':'H','target':0}]*2,'shots':0,'seed':0}
        r=simulate_quantum(p)
        self.assertAlmostEqual(r['probabilities']['0'],1.0)
        self.assertAlmostEqual(r['probabilities']['1'],0.0)

    def test_z_changes_phase_not_probability(self):
        p={'qubits':1,'initial_basis':1,'gates':[{'gate':'Z','target':0}],'shots':0,'seed':0}
        r=simulate_quantum(p)
        self.assertEqual(r['probabilities']['1'],1.0)

    def test_shots_deterministic(self):
        p=dict(BELL,shots=100,seed=42)
        self.assertEqual(simulate_quantum(p)['sampled_counts'],simulate_quantum(p)['sampled_counts'])
        self.assertEqual(sum(simulate_quantum(p)['sampled_counts'].values()),100)
        self.assertIsNone(simulate_quantum(BELL)['sampled_counts'])

    def test_bad_gate_and_resource_limits(self):
        failures=[dict(BELL,qubits=7),dict(BELL,shots=1025),dict(BELL,seed=True),
                  dict(BELL,gates=[{'gate':'H','target':0}]*129),
                  dict(BELL,gates=[{'gate':'RX','target':0}]),
                  dict(BELL,gates=[{'gate':'CNOT','target':0,'control':0}]),
                  dict(BELL,gates=[{'gate':'H','target':3}]),
                  dict(BELL,extra='not allowed'),dict(BELL,initial_basis=float('nan'))]
        for bad in failures:
            with self.subTest(bad=str(bad)[:80]), self.assertRaises(ValueError):
                simulate_quantum(bad)
        for budget in (0,True,11,1000001):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                simulate_quantum(BELL,budget_units=budget)

    def test_does_not_mutate_math_problem(self):
        p=copy.deepcopy(BELL)
        simulate_quantum(p)
        self.assertEqual(p,BELL)


if __name__=='__main__':unittest.main()
