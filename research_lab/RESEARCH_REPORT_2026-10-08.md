# GPT-Doug Research Log — Exact Singularities, 8 October 2026

## Research integrity statement

**Scope:** scalar autonomous ODEs with rational polynomial coefficients and a
classical, smooth divergence-free field-scaling obstruction relevant to the
3-dimensional incompressible Navier-Stokes equations. **No new theorem, no
Millennium Prize solution, and no novel mathematical priority is asserted.**

## Result A — exact singularity and a stronger machine-checkable certificate

Consider

    x'(t)=2*x(t)^2-4*x(t)+4,       x(0)=1.

Let `y=x-1`. Then `y'=2(1+y^2)` and `y(0)=0`. Separation gives
`arctan(y)=2t`, so

    x(t)=1+tan(2t),     0 <= t < pi/4.

The first finite-time blow-up occurs at `T=pi/4` with `x(t)->+infinity`.
SymPy 1.14 returned exact zero on substitution into the differential equation.

The comparison `P(x)>=x^2` follows from the exact polynomial identity

    P(x)-x^2 = (x-2)^2.

For `x>=1`, `x'>=x^2`, giving the independently verified blow-up bound
`T<=1`. The old sign-of-coefficients method failed because, with `z=x-1`,
`(x-2)^2=(z-1)^2=z^2-2z+1` has a negative coefficient. The new exact
rational SOS prover emits `1*(z-1)^2` as a machine-replayable certificate.

`P(x)/x^2 = 1+(1-2/x)^2`, so `a=1` is the *optimal constant* in the
comparison `P(x)>=a*x^2` for all `x>=1`. The comparison bound 1 is not the
exact blow-up time; the exact time is pi/4.

## Result B — complete exact forward-time dichotomy for quadratic scalar ODEs

**Theorem (classical Riccati phase-line classification).** Given rational
`A>0`, `B`, `C` and `x0>0`, the unique maximal forward-time solution to

    x'=A*x^2+B*x+C,    x(0)=x0

has exactly one of three behaviors:

1. It is constant because `P(x0)=0`.
2. It blows up to `+infinity` at finite positive time.
3. It exists for all forward time and remains in a bounded interval.

The `singularity_quadratic.decide()` implementation produces an exact
certificate for each case; `verify()` independently replays it.

**Certificate derivation.** Set

    m=inf_{x>=x0} P(x)/x^2.

With `y=1/x`, this is the minimum of `A+B*y+C*y^2` on the compact interval
`[0,1/x0]`. The minimum is rational and is attained at one of the endpoints
or, when `C>0`, the quadratic vertex `y=-B/(2*C)` if interior. Hence `m` is
calculated exactly without a floating-point root finder.

* If `P(x0)=0`, polynomial ODE uniqueness gives the constant equilibrium.
* If `m>0`, then for all `x>=x0`, `x'>=m*x^2`. Comparison gives finite-time
  `+infinity` blow-up by `T<=1/(m*x0)`. The quadratic nonnegative gap
  `P(x0+z)-m*(x0+z)^2` admits an exact rational weighted sum-of-squares
  certificate on `z>=0` (including terms multiplied by `z`).
* If `m<=0` and `P(x0)<0`, choose
  `R=1+max(|B|/A,|C|/A)`. Then `P(-R)>0` by the root bound, while
  `P(x0)<0`, so `[-R,x0]` is forward invariant.
* If `m<=0` and `P(x0)>0`, the polynomial must have a minimum at
  `v=-B/(2*A)>x0` with `P(v)<=0`. Hence `[x0,v]` is forward invariant.

In the last two cases, local Lipschitzness plus bounded continuation yields a
solution for all forward time. This proves the trichotomy and exact proof
certificate construction for the stated *scalar quadratic* class.

**Finite exhaustive grid check:** `A` in `{1/2,1,2}`, `B,C` in
`{-8,-7,...,8}`, `x0` in `{1/4,1/2,1,2,4}`, totaling 4,335 models.
The checker replayed every certificate with exact fractions:

- Finite-time blow-up: 2,364
- Globally bounded: 1,892
- Equilibria: 79

The test suite includes additional randomized quadratic and higher-degree SOS
cases, adversarial tampering of proof fields, CLI round trips, and exact
symbolic solution verification.

## Result C — exact obstruction to an energy-only fluid-regularity argument

Define `r^2=x^2+y^2+z^2` and the smooth rapidly decaying vector field

    phi(x,y,z)=(-2*y*exp(-r^2), 2*x*exp(-r^2), 0).

It is divergence-free because the x and y partial derivatives cancel:

    div(phi)=4*x*y*exp(-r^2)-4*x*y*exp(-r^2)=0.

Direct Gaussian integration gives

    ||phi||_L2^2 = pi^(3/2)/sqrt(2),
    ||phi||_Linfinity = sqrt(2/e).

For every scale `lambda>0`, let

    phi_lambda(x)=lambda^(3/2)*phi(lambda*x).

By substitution in the integral,

    ||phi_lambda||_L2^2 = ||phi||_L2^2,
    ||phi_lambda||_Linfinity = lambda^(3/2)*sqrt(2/e).

Therefore the supremum norm can become arbitrarily large even though the
kinetic energy is exactly fixed for a sequence of smooth, divergence-free,
rapidly decaying vector fields. **This does not exhibit a Navier-Stokes
singularity.** The fields are a family of possible initial data, not a single
Navier-Stokes solution evolving in time. This known scaling obstruction shows
that an L2 energy estimate by itself cannot bound peak velocity independently
of stronger regularity assumptions.

## Reproduce

From the repository root with Python 3.9 or newer:

    python3 -m research_lab.singularity_sos demo
    python3 -m research_lab.singularity_sos prove --coeffs '4,-4,2' --x0 1 --p 2 --a 1
    python3 -m research_lab.singularity_quadratic decide --coeffs '4,-4,2' --x0 1
    python3 -m research_lab.singularity_quadratic decide --coeffs '4,-4,1' --x0 1
    python3 -m unittest discover -s research_lab/tests -p 'test_singularity*.py' -q

The base `research_lab/singularity.py` is from GPT-Doug's preceding prototype.
All scripts run locally with Python's standard library. The optional exact
symbolic cross-check used SymPy 1.14 in the development container, but SymPy
is not required for the proof engine.

## Open frontiers and evaluation gates

The next natural targets are rigorous two- and three-component model reductions,
computer-checkable barriers for PDEs, a Lean/Mathlib checker for comparison
lemmas, and numerical schemes with *proved* error bounds. The 3D **unforced**
Navier-Stokes global-regularity question cannot be settled by these scalar-ODE
results; energy concentration, nonlinear pressure and spatial regularity are
substantial missing obstacles. Every future breakthrough claim requires an
exact problem statement, valid proof, independent review, and reproducible
formal or mathematical checking.