"""Exact Fourier certificate engine for a class of 3D unforced Navier-Stokes flows.

The mathematical result is CLASSICAL, not a solution to general 3D regularity.
For a real finite Fourier field V on (R/2pi Z)^3 with div V=0 and
curl V=lambda V, the unforced viscous Navier-Stokes solution is
  u(t,x)=exp(-nu*lambda**2*t)*V(x)
  p(t,x)=-exp(-2*nu*lambda**2*t)*|V(x)|**2/2.
This module checks the underlying finite Fourier identities exactly using
Gaussian rational arithmetic, including explicit nonlinear convolution.
No numerical sampling, model calls or network access are involved.
"""

import argparse
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ZERO = (Fraction(0), Fraction(0))
ZVEC = (ZERO, ZERO, ZERO)
MAX_MODES = 64
MAX_WAVENUMBER = 1000


def _rat(value):
    if isinstance(value, (bool, float)):
        raise ValueError('exact rational strings or integers required; floats are disallowed')
    if not isinstance(value, (str, int, Fraction)):
        raise ValueError('invalid rational value type')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('invalid rational') from exc


def _gauss(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (_rat(value[0]), _rat(value[1]))
    raise ValueError('coefficient must be [real, imaginary], with exact rationals')


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _neg(a):
    return (-a[0], -a[1])


def _mul(a, b):
    return (a[0]*b[0]-a[1]*b[1], a[0]*b[1]+a[1]*b[0])


def _scale(a, factor):
    return (a[0]*factor, a[1]*factor)


def _imaginary(a):
    return (-a[1], a[0])


def _conj(a):
    return (a[0], -a[1])


def _qstr(a):
    return [str(a[0]), str(a[1])]


def _norm_sq(a):
    return a[0]**2 + a[1]**2


def _sum_complex(values):
    total = ZERO
    for value in values:
        total = _add(total, value)
    return total


def _dot(a, b):
    return _sum_complex(_mul(x, y) for x, y in zip(a, b))


def _with_modes(field):
    if not isinstance(field, (list, tuple)) or not 1 <= len(field) <= MAX_MODES:
        raise ValueError('field must have 1 through 64 Fourier mode objects')
    modes = {}
    for item in field:
        if not isinstance(item, dict):
            raise ValueError('mode entries must be objects')
        k = item.get('k')
        vec = item.get('a')
        if not isinstance(k, (list, tuple)) or len(k) != 3:
            raise ValueError('mode index k must contain 3 integers')
        if any(isinstance(c, bool) or not isinstance(c, int) or
               abs(c) > MAX_WAVENUMBER for c in k):
            raise ValueError('mode indices must be bounded integers')
        k = tuple(k)
        if k == (0, 0, 0):
            raise ValueError('the nonzero-curl family requires nonzero wavevectors')
        if k in modes:
            raise ValueError('duplicate Fourier wavevectors are not accepted')
        if not isinstance(vec, (list, tuple)) or len(vec) != 3:
            raise ValueError('mode amplitude must have 3 vector components')
        parsed = tuple(_gauss(component) for component in vec)
        if all(v == ZERO for v in parsed):
            raise ValueError('explicit zero modes are not accepted')
        modes[k] = parsed
    return modes


def _serialize(modes):
    return [
        {'k': list(k), 'a': [_qstr(c) for c in modes[k]]}
        for k in sorted(modes)
    ]


def _reality(modes):
    for k, vec in modes.items():
        other = modes.get(tuple(-n for n in k))
        if other is None or other != tuple(_conj(component) for component in vec):
            return False
    return True


def _divergence(modes):
    for k, a in modes.items():
        if _sum_complex(_scale(a[j], k[j]) for j in range(3)) != ZERO:
            return False
    return True


def _curl_eigenfield(modes, hel):
    for k, a in modes.items():
        cross = (
            _add(_scale(a[2], k[1]), _scale(a[1], -k[2])),
            _add(_scale(a[0], k[2]), _scale(a[2], -k[0])),
            _add(_scale(a[1], k[0]), _scale(a[0], -k[1])),
        )
        if any(_imaginary(cross[j]) != _scale(a[j], hel) for j in range(3)):
            return False
        if sum(x*x for x in k) != hel*hel:
            return False
    return True


def _convolution_residuals(modes):
    """Calculate (V.grad)V + grad(-|V|^2/2) mode-by-mode exactly."""
    nonlin = defaultdict(lambda: [ZERO, ZERO, ZERO])
    pressure = defaultdict(lambda: ZERO)
    items = list(modes.items())
    for k, a in items:
        for l, b in items:
            q = tuple(k[j] + l[j] for j in range(3))
            velocity_times_wave = _sum_complex(_scale(a[j], l[j]) for j in range(3))
            for j in range(3):
                term = _imaginary(_mul(velocity_times_wave, b[j]))
                nonlin[q][j] = _add(nonlin[q][j], term)
            pressure[q] = _add(pressure[q], _scale(_dot(a, b), Fraction(-1, 2)))
    for q in set(nonlin) | set(pressure):
        for j in range(3):
            pressure_gradient = _imaginary(_scale(pressure[q], q[j]))
            if _add(nonlin[q][j], pressure_gradient) != ZERO:
                return False, pressure
    return True, pressure


def certify(modes_input, helicity, viscosity):
    """Return a complete replayable proof object, or raise on invalid claims."""
    modes = _with_modes(modes_input)
    hel, nu = _rat(helicity), _rat(viscosity)
    if hel == 0 or nu <= 0:
        raise ValueError('nonzero curl eigenvalue and positive viscosity required')
    if not _reality(modes):
        raise ValueError('field fails real-valuedness (conjugate symmetry)')
    if not _divergence(modes):
        raise ValueError('field is not divergence-free')
    if not _curl_eigenfield(modes, hel):
        raise ValueError('curl field is not the requested exact eigenfunction')
    cancelled, pressure = _convolution_residuals(modes)
    if not cancelled:
        raise ValueError('nonlinear term and pressure do not cancel exactly')
    energy_coefficient = sum(
        _norm_sq(a) for vec in modes.values() for a in vec
    )
    if energy_coefficient <= 0:
        raise ValueError('field must be nonzero')
    pressure_constant = pressure.get((0, 0, 0), ZERO)
    if pressure_constant != (-energy_coefficient / 2, Fraction(0)):
        raise ValueError('Parseval coefficient and pressure convolution disagree')
    component_bounds = [
        sum(abs(a[j][0]) + abs(a[j][1]) for a in modes.values())
        for j in range(3)
    ]
    return {
        'status': 'CERTIFIED_GLOBAL_SMOOTH_SPECIAL_CLASS',
        'proof_scope': 'Unforced 3D periodic Navier-Stokes, finite real Beltrami Fourier fields',
        'domain': '(R/2pi Z)^3',
        'viscosity': str(nu),
        'curl_eigenvalue': str(hel),
        'modes': _serialize(modes),
        'mode_count': len(modes),
        'pressure_mode_count': sum(bool(any(pressure[k][j] != 0 for j in (0, 1)))
                                   for k in pressure),
        'exact_divergence_residual': '0',
        'exact_curl_residual': '0',
        'exact_nonlinear_pressure_residual': '0',
        'exact_linear_heat_residual': '0',
        'kinetic_energy_l2_coefficient': str(energy_coefficient),
        'kinetic_energy': '(2*pi)^3/2 * kinetic_energy_l2_coefficient * exp(-2*nu*lambda^2*t)',
        'helicity_coefficient': str(hel * energy_coefficient),
        'component_sup_bounds': [str(b) for b in component_bounds],
        'velocity_sup_bound_squared_coefficient': str(sum(b*b for b in component_bounds)),
        'solution_velocity': 'u(t,x) = exp(-nu*lambda^2*t) * V(x)',
        'solution_pressure': 'p(t,x) = -exp(-2*nu*lambda^2*t)*|V(x)|^2/2',
        'verification_note': 'EXACT identities for a restricted known solution class; NOT a universal regularity proof',
    }


def verify(certificate):
    if not isinstance(certificate, dict):
        return False
    try:
        duplicate = certify(certificate['modes'], certificate['curl_eigenvalue'],
                            certificate['viscosity'])
        return certificate == duplicate
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def abc_modes(A='1', B='1', C='1', wave=1):
    """Return exact coefficients for Arnold-Beltrami-Childress 3D flow."""
    if isinstance(wave, bool) or not isinstance(wave, int) or not 1 <= wave <= MAX_WAVENUMBER:
        raise ValueError('ABC wavenumber must be a positive integer')
    amps = (_rat(A), _rat(B), _rat(C))
    entries = {}
    def add_term(component, axis, kind, amplitude):
        if amplitude == 0:
            return
        for sign in (1, -1):
            kk = [0, 0, 0]
            kk[axis] = sign*wave
            key = tuple(kk)
            if key not in entries:
                entries[key] = [ZERO, ZERO, ZERO]
            value = (amplitude / 2, Fraction(0)) if kind == 'cos' else (
                Fraction(0), -sign*amplitude / 2)
            entries[key][component] = _add(entries[key][component], value)
    a, b, c = amps
    add_term(0, 2, 'sin', a)
    add_term(0, 1, 'cos', c)
    add_term(1, 0, 'sin', b)
    add_term(1, 2, 'cos', a)
    add_term(2, 1, 'sin', c)
    add_term(2, 0, 'cos', b)
    return _serialize({k: tuple(v) for k, v in entries.items()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('demo')
    abc = sub.add_parser('abc', help='certify global ABC family for rational amplitudes')
    for name in ('a', 'b', 'c'):
        abc.add_argument('--' + name, default='1')
    abc.add_argument('--k', type=int, default=1)
    abc.add_argument('--nu', default='1')
    inp = sub.add_parser('certify', help='read mode list, helicity and viscosity JSON')
    inp.add_argument('file', type=Path)
    chk = sub.add_parser('verify', help='verify a previously emitted certificate')
    chk.add_argument('file', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == 'demo':
            out = certify(abc_modes(1, 2, 3, 1), 1, '1/10')
        elif args.action == 'abc':
            out = certify(abc_modes(args.a, args.b, args.c, args.k),
                          args.k, args.nu)
        elif args.action == 'certify':
            data = json.loads(args.file.read_text(encoding='utf-8'))
            out = certify(data['modes'], data['curl_eigenvalue'], data['viscosity'])
        else:
            data = json.loads(args.file.read_text(encoding='utf-8'))
            ok = verify(data)
            out = {'status': 'VERIFIED' if ok else 'INVALID'}
        print(json.dumps(out, indent=2, sort_keys=True, allow_nan=False))
        return 1 if out['status'] == 'INVALID' else 0
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'ERROR', 'message': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
