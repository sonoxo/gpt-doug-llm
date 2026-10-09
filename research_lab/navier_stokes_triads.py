"""Exact finite Fourier triad interactions for unforced 3D fluid research.

Computes the Leray-projected nonlinear term P[(u.grad)u] for a finite
real divergence-free trigonometric polynomial on the periodic 3-torus.
This is an instantaneous diagnostic, NOT a full time evolution, proof of
regularity or blow-up, or a new mathematical theorem.
"""

import argparse
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from . import navier_stokes_beltrami as b


def _projection(modes):
    transported = defaultdict(lambda: [b.ZERO, b.ZERO, b.ZERO])
    for wave, a in modes.items():
        for other, c in modes.items():
            q = tuple(wave[j] + other[j] for j in range(3))
            qdot = b._sum_complex(b._scale(a[j], other[j]) for j in range(3))
            for j in range(3):
                transported[q][j] = b._add(
                    transported[q][j], b._imaginary(b._mul(qdot, c[j]))
                )
    projected = {}
    for q, n in transported.items():
        length_sq = sum(z*z for z in q)
        if length_sq == 0:
            # Periodic divergence-free transport has zero spatial mean.
            if any(component != b.ZERO for component in n):
                raise ValueError('zero mode violates exact mean-advection cancellation')
            continue
        divergence = b._sum_complex(b._scale(n[j], q[j]) for j in range(3))
        result = tuple(
            b._add(n[j], b._neg(b._scale(divergence, Fraction(q[j], length_sq))))
            for j in range(3)
        )
        if any(component != b.ZERO for component in result):
            projected[q] = result
            divergence_after = b._sum_complex(b._scale(result[j], q[j])
                                                  for j in range(3))
            if divergence_after != b.ZERO:
                raise ValueError('nonlinearity projection failed to be divergence-free')
    return projected


def diagnose(mode_list):
    """Exact pressure-projected advection, Parseval energy and transfer checks."""
    modes = b._with_modes(mode_list)
    if not b._reality(modes) or not b._divergence(modes):
        raise ValueError('input must be real and divergence-free')
    projected = _projection(modes)
    energy_transfer = b.ZERO
    enstrophy_transfer = b.ZERO
    for k, a in modes.items():
        n = projected.get(k, b.ZVEC)
        term = b._dot(tuple(b._conj(x) for x in a), n)
        energy_transfer = b._add(energy_transfer, term)
        enstrophy_transfer = b._add(
            enstrophy_transfer, b._scale(term, sum(q*q for q in k))
        )
    if energy_transfer != b.ZERO:
        raise ValueError('periodic nonlinear energy cancellation failed')
    if enstrophy_transfer[1] != 0:
        raise ValueError('real enstrophy transfer must have zero imaginary part')
    energy = sum(b._norm_sq(a) for v in modes.values() for a in v)
    return {
        'status': 'EXACT_INSTANTANEOUS_TRIAD_DIAGNOSTIC',
        'domain': '(R/2pi Z)^3',
        'input_modes': b._serialize(modes),
        'input_l2_energy_coefficient': str(energy),
        'nonzero_projected_mode_count': len(projected),
        'projected_nonlinearity': [
            {'k': list(k), 'a': [b._qstr(c) for c in projected[k]]}
            for k in sorted(projected)
        ],
        'exact_energy_transfer': [str(energy_transfer[0]), str(energy_transfer[1])],
        'exact_enstrophy_transfer': [str(enstrophy_transfer[0]),
                                     str(enstrophy_transfer[1])],
        'scope': 'Fourier transport at one instant only; no PDE continuation bound',
    }


def verify(certificate):
    if not isinstance(certificate, dict):
        return False
    try:
        return certificate == diagnose(certificate['input_modes'])
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


def demo_modes():
    """Two individually Beltrami waves with different curl eigenvalues."""
    return b.abc_modes(1, 0, 0, 1) + b.abc_modes(0, 1, 0, 2)



def initial_derivatives(mode_list, amplitude, viscosity):
    """Compute exact t=0 energy and gradient-norm rates for a smooth NS datum.

    The datum is a real finite Fourier polynomial scaled by `amplitude`.
    Local smooth NS existence is classical. This computes instantaneous
    derivatives only, not persistence, regularity or singularity.
    """
    a = b._rat(amplitude)
    nu = b._rat(viscosity)
    if a == 0 or nu <= 0:
        raise ValueError('nonzero amplitude and positive viscosity required')
    modes = b._with_modes(mode_list)
    diagnostic = diagnose(b._serialize(modes))
    enstrophy = sum(
        sum(z*z for z in k) * sum(b._norm_sq(c) for c in vec)
        for k, vec in modes.items()
    )
    laplace_sq = sum(
        (sum(z*z for z in k)**2) * sum(b._norm_sq(c) for c in vec)
        for k, vec in modes.items()
    )
    interaction = b._rat(diagnostic['exact_enstrophy_transfer'][0])
    k_derivative = -nu*a*a*enstrophy
    h_derivative = -2*(nu*a*a*laplace_sq + a*a*a*interaction)
    return {
        'status': ('ENSTROPHY_INCREASES_AT_T0' if h_derivative > 0
                   else 'ENSTROPHY_NONINCREASING_AT_T0'),
        'domain': '(R/2pi Z)^3',
        'input_modes': b._serialize(modes),
        'amplitude': str(a),
        'viscosity': str(nu),
        'base_enstrophy_coefficient': str(enstrophy),
        'base_laplacian_squared_coefficient': str(laplace_sq),
        'base_nonlinear_enstrophy_transfer': str(interaction),
        'kinetic_energy_derivative_per_torus_volume': str(k_derivative),
        'gradient_l2_squared_derivative_per_torus_volume': str(h_derivative),
        'scope': 'exact derivative at t=0 only, assuming classical local smooth solution',
    }


def verify_initial_derivatives(certificate):
    if not isinstance(certificate, dict):
        return False
    try:
        return certificate == initial_derivatives(
            certificate['input_modes'], certificate['amplitude'],
            certificate['viscosity'])
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    d = sub.add_parser('diagnose')
    d.add_argument('file', type=Path)
    v = sub.add_parser('verify')
    v.add_argument('file', type=Path)
    growth = sub.add_parser('growth', help='exact instantaneous energy/enstrophy rates')
    growth.add_argument('file', type=Path)
    growth.add_argument('--amplitude', default='1')
    growth.add_argument('--nu', default='1')
    growth_verify = sub.add_parser('verify-growth')
    growth_verify.add_argument('file', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            output = diagnose(demo_modes())
        elif args.command == 'diagnose':
            data = json.loads(args.file.read_text(encoding='utf-8'))
            output = diagnose(data['input_modes'])
        elif args.command == 'growth':
            data = json.loads(args.file.read_text(encoding='utf-8'))
            output = initial_derivatives(data['input_modes'], args.amplitude, args.nu)
        else:
            data = json.loads(args.file.read_text(encoding='utf-8'))
            is_valid = (verify(data) if args.command == 'verify'
                        else verify_initial_derivatives(data))
            output = {'status': 'VERIFIED' if is_valid else 'INVALID'}
        print(json.dumps(output, indent=2, sort_keys=True))
        return int(output['status'] == 'INVALID')
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'ERROR', 'message': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
