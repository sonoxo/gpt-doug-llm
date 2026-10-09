"""End-to-end checks for Fourier exact 3D unforced NS special solutions."""
import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_lab import navier_stokes_beltrami as b


class BeltramiCertificates(unittest.TestCase):
    def test_exact_abc(self):
        cert = b.certify(b.abc_modes(1, 2, 3), 1, '1/10')
        self.assertEqual(cert['kinetic_energy_l2_coefficient'], '14')
        self.assertEqual(cert['helicity_coefficient'], '14')
        self.assertEqual(cert['velocity_sup_bound_squared_coefficient'], '50')
        self.assertTrue(b.verify(cert))

    def test_abc_pressure_has_nonlinearity(self):
        cert = b.certify(b.abc_modes(1, 2, 3), 1, 1)
        self.assertGreater(cert['pressure_mode_count'], 1)
        self.assertEqual(cert['exact_nonlinear_pressure_residual'], '0')

    def test_non_axis_helical_wave_and_superposition(self):
        # k=(2,2,1), |k|=3; v=(1,-1,0), w=(k cross v)/3.
        # a=v+i*w is a positive-helicity eigenvector with exact rationals.
        amp = [['1', '1/3'], ['-1', '1/3'], ['0', '-4/3']]
        anti = [['1', '-1/3'], ['-1', '-1/3'], ['0', '4/3']]
        data = b.abc_modes(1, 2, 3, 3)
        data += [{'k': [2, 2, 1], 'a': amp},
                 {'k': [-2, -2, -1], 'a': anti}]
        cert = b.certify(data, 3, '7/13')
        self.assertEqual(cert['kinetic_energy_l2_coefficient'], '22')
        self.assertTrue(b.verify(cert))

    def test_negative_helicity(self):
        data = b.abc_modes(1, 2, 3, 2)
        for entry in data:
            for comp in entry['a']:
                comp[1] = str(-b._rat(comp[1]))
        cert = b.certify(data, -2, '1/7')
        self.assertTrue(b.verify(cert))

    def test_negative_amplitudes(self):
        cert = b.certify(b.abc_modes('-1/2', '-5/3', '3/4'), 1, '2/5')
        self.assertTrue(b.verify(cert))

    def test_larger_wavenumber(self):
        cert = b.certify(b.abc_modes(1, 2, 3, 7), 7, '1/3')
        self.assertTrue(b.verify(cert))

    def test_one_mode_axis(self):
        for a, bb, c in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            with self.subTest(a=a, b=bb, c=c):
                self.assertTrue(b.verify(b.certify(b.abc_modes(a, bb, c), 1, 1)))

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            b.certify(b.abc_modes(0, 0, 0), 1, 1)

    def test_wrong_helicity_rejected(self):
        with self.assertRaises(ValueError):
            b.certify(b.abc_modes(1, 2, 3), -1, 1)

    def test_wrong_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            b.certify(b.abc_modes(1, 2, 3, 2), 1, 1)

    def test_negative_viscosity_rejected(self):
        with self.assertRaises(ValueError):
            b.certify(b.abc_modes(1, 2, 3), 1, 0)

    def test_numerical_float_rejected(self):
        with self.assertRaises(ValueError):
            b.abc_modes(0.1, 1, 1)
        with self.assertRaises(ValueError):
            b.certify(b.abc_modes(), 1, 1.2)

    def test_broken_reality_rejected(self):
        modes = b.abc_modes(1, 2, 3)
        modes.pop()
        with self.assertRaises(ValueError):
            b.certify(modes, 1, 1)

    def test_broken_divergence_rejected(self):
        modes = b.abc_modes(1, 2, 3)
        for entry in modes:
            if entry['k'] == [1, 0, 0]:
                entry['a'][0] = ['1/8', '0']
            if entry['k'] == [-1, 0, 0]:
                entry['a'][0] = ['1/8', '0']
        with self.assertRaises(ValueError):
            b.certify(modes, 1, 1)

    def test_duplicate_rejected(self):
        modes = b.abc_modes()
        modes.append(modes[0])
        with self.assertRaises(ValueError):
            b.certify(modes, 1, 1)

    def test_tampering_energy(self):
        cert = b.certify(b.abc_modes(), 1, 1)
        forged = copy.deepcopy(cert)
        forged['kinetic_energy_l2_coefficient'] = '99999'
        self.assertFalse(b.verify(forged))

    def test_tampering_mode(self):
        cert = b.certify(b.abc_modes(), 1, 1)
        forged = copy.deepcopy(cert)
        forged['modes'][0]['a'][0][0] = '999'
        self.assertFalse(b.verify(forged))

    def test_tampering_status(self):
        cert = b.certify(b.abc_modes(), 1, 1)
        forged = dict(cert)
        forged['status'] = 'SOLVED_MILLENNIUM_PROBLEM'
        self.assertFalse(b.verify(forged))

    def test_tampering_scope(self):
        cert = b.certify(b.abc_modes(), 1, 1)
        forged = dict(cert)
        forged['proof_scope'] = 'All smooth initial data'
        self.assertFalse(b.verify(forged))

    def test_modes_exact_conjugate(self):
        v = b._with_modes(b.abc_modes('1/3', '2/5', '-7/9'))
        self.assertTrue(b._reality(v))
        self.assertTrue(b._divergence(v))
        self.assertTrue(b._curl_eigenfield(v, 1))
        self.assertTrue(b._convolution_residuals(v)[0])

    def test_multi_group_random_linear_combination(self):
        random.seed(1169)
        for _ in range(200):
            k = random.randint(1, 10)
            a, bb, c = [str(random.randint(-50, 50)) + '/' +
                         str(random.randint(1, 19)) for j in range(3)]
            modes = b.abc_modes(a, bb, c, k)
            self.assertTrue(b.verify(b.certify(modes, k, '1/5')))

    def test_cli_roundtrip(self):
        cmd = [sys.executable, '-m', 'research_lab.navier_stokes_beltrami']
        process = subprocess.run(cmd + ['abc', '--a', '1', '--b', '2', '--c', '3',
                                        '--k', '2', '--nu', '1/4'],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        cert = json.loads(process.stdout)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'cert.json'
            path.write_text(process.stdout)
            proc = subprocess.run(cmd + ['verify', str(path)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertEqual(json.loads(proc.stdout)['status'], 'VERIFIED')

    def test_bad_input_exit(self):
        proc = subprocess.run([sys.executable, '-m', 'research_lab.navier_stokes_beltrami',
                               'abc', '--nu', '0'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
