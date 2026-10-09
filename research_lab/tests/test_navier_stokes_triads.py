"""Exact tests for projected nonlinear Fourier interactions."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_lab import navier_stokes_beltrami as b
from research_lab import navier_stokes_triads as t


class TriadTests(unittest.TestCase):
    def test_individual_eigenflows_nonlin_zero(self):
        for params in [(1, 0, 0, 1), (0, 1, 0, 2), (1, 2, 3, 1)]:
            with self.subTest(params=params):
                d = t.diagnose(b.abc_modes(*params))
                self.assertEqual(d['nonzero_projected_mode_count'], 0)
                self.assertTrue(t.verify(d))

    def test_mixed_eigenvalues_create_new_modes(self):
        d = t.diagnose(t.demo_modes())
        self.assertEqual(d['nonzero_projected_mode_count'], 4)
        self.assertEqual(d['exact_energy_transfer'], ['0', '0'])
        nonlinearity = {tuple(e['k']):e['a'] for e in d['projected_nonlinearity']}
        self.assertEqual(nonlinearity[(-2, 0, -1)],
                         [['-3/20', '0'], ['0', '1/4'], ['3/10', '0']])
        self.assertTrue(t.verify(d))

    def test_enstrophy_initial_growth_exact(self):
        from pathlib import Path
        import json
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / 'research_lab/examples/enstrophy_growth_initial_data.json').read_text())
        result = t.initial_derivatives(data['input_modes'], 10, 1)
        self.assertEqual(result['status'], 'ENSTROPHY_INCREASES_AT_T0')
        self.assertEqual(result['kinetic_energy_derivative_per_torus_volume'], '-8400')
        self.assertEqual(result['gradient_l2_squared_derivative_per_torus_volume'], '15200')
        self.assertTrue(t.verify_initial_derivatives(result))
        result['gradient_l2_squared_derivative_per_torus_volume'] = '15201'
        self.assertFalse(t.verify_initial_derivatives(result))

    def test_enstrophy_initial_dissipation(self):
        from pathlib import Path
        import json
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / 'research_lab/examples/enstrophy_growth_initial_data.json').read_text())
        result = t.initial_derivatives(data['input_modes'], 1, 1)
        self.assertEqual(result['gradient_l2_squared_derivative_per_torus_volume'], '-208')
        self.assertEqual(result['status'], 'ENSTROPHY_NONINCREASING_AT_T0')
        self.assertTrue(t.verify_initial_derivatives(result))

    def test_tampering_rejected(self):
        d = t.diagnose(t.demo_modes())
        tampered = copy.deepcopy(d)
        tampered['projected_nonlinearity'][0]['a'][0][0] = '777'
        self.assertFalse(t.verify(tampered))

    def test_scope_tamper_rejected(self):
        d = t.diagnose(t.demo_modes())
        d['scope'] = 'Proof of global regularity'
        self.assertFalse(t.verify(d))

    def test_reject_non_divergence(self):
        modes = b.abc_modes()
        for e in modes:
            if e['k'] == [1, 0, 0] or e['k'] == [-1, 0, 0]:
                e['a'][0] = ['1', '0']
        with self.assertRaises(ValueError):
            t.diagnose(modes)

    def test_cli(self):
        cmd = [sys.executable, '-m', 'research_lab.navier_stokes_triads']
        r = subprocess.run(cmd + ['demo'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'triad.json'
            path.write_text(r.stdout)
            ver = subprocess.run(cmd+['verify',str(path)], capture_output=True, text=True)
            self.assertEqual(json.loads(ver.stdout)['status'], 'VERIFIED')


if __name__ == '__main__':
    unittest.main()
